import logging

from django.conf import settings
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .providers import (
    ProviderError,
    WebhookVerificationError,
    YocoProvider,
    get_provider,
)
from .serializers import PaymentInitiateSerializer
from audit.services import create_audit_log

from .services import (
    PaymentMismatchError,
    initiate_payment,
    process_payment_webhook,
    process_yoco_event,
)

logger = logging.getLogger(__name__)


class PaymentInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            provider = get_provider()
            payment, provider_result = initiate_payment(
                user=request.user,
                order_id=serializer.validated_data["order_id"],
                provider=provider,
            )
        except ProviderError as exc:
            logger.warning("Payment provider error: %s", exc)
            return Response(
                {"detail": "The payment provider is unavailable. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "payment_id": payment.id,
                "order_id": payment.order_id,
                "provider": payment.provider,
                "amount": payment.amount,
                "currency": payment.currency,
                "status": payment.status,
                "checkout_url": provider_result["checkout_url"],
            },
            status=status.HTTP_201_CREATED,
        )


class PaymentWebhookView(APIView):
    """
    Unauthenticated webhook for the fake "test" provider.

    It only exists in DEBUG / test runs. In production this URL returns 404 and
    real providers use their own signature-verified endpoints (e.g. /yoco/).
    """

    authentication_classes = []
    permission_classes = []
    throttle_scope = "webhook"

    def post(self, request):
        if not settings.PAYMENT_TEST_PROVIDER_ENABLED:
            return Response(status=status.HTTP_404_NOT_FOUND)

        event_id = request.headers.get("X-Webhook-Event-ID")
        event_type = request.headers.get("X-Webhook-Event-Type")

        if not event_id:
            return Response(
                {"detail": "Webhook event ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not event_type:
            return Response(
                {"detail": "Webhook event type is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            _, payment = process_payment_webhook(
                provider="test",
                event_id=event_id,
                event_type=event_type,
                payload=request.data,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "processed": True,
                "payment_id": payment.id if payment else None,
            },
            status=status.HTTP_200_OK,
        )


class YocoWebhookView(APIView):
    """Signature-verified webhook for Yoco (payment.succeeded, refund.*)."""

    authentication_classes = []
    permission_classes = []
    throttle_scope = "webhook"

    def post(self, request):
        # Read the raw body first: the signature covers the exact bytes.
        raw_body = request.body

        try:
            event = YocoProvider.verify_webhook(
                headers=request.headers,
                raw_body=raw_body,
            )
        except WebhookVerificationError as exc:
            logger.warning("Rejected Yoco webhook: %s", exc)
            return Response(
                {"detail": "Invalid webhook signature."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            _, payment = process_yoco_event(event=event)
        except PaymentMismatchError as exc:
            create_audit_log(
                action="PAYMENT_AMOUNT_MISMATCH",
                model_name="Payment",
                object_id=exc.payment_id,
                details={"expected_cents": exc.expected, "received": exc.received},
            )
            logger.error("Yoco payment amount mismatch: %s", exc)
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValueError as exc:
            logger.warning("Yoco webhook could not be processed: %s", exc)
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"processed": True, "payment_id": payment.id if payment else None},
            status=status.HTTP_200_OK,
        )
