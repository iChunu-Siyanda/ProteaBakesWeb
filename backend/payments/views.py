from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import PaymentInitiateSerializer
from .services import PaymentProvider, initiate_payment, process_payment_webhook


class PaymentInitiateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = PaymentInitiateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            payment, provider_result = initiate_payment(
                user=request.user,
                order_id=serializer.validated_data["order_id"],
                provider=PaymentProvider(),
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
    permission_classes = []

    def post(self, request):
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
