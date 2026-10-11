from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from audit.services import create_audit_log
from notifications.events import notify_payment_failed
from orders.models import Order
from orders.services import change_order_status

from .models import Payment, WebhookEvent
from .providers import (
    FakePaymentProvider,
    ProviderError,  # noqa: F401  (re-exported for callers)
    to_cents,
)

class PaymentMismatchError(ValueError):
    """The provider reported a payment that doesn't match our order."""

    def __init__(self, message, *, payment_id, expected, received):
        super().__init__(message)
        self.payment_id = payment_id
        self.expected = expected
        self.received = received


# Backwards-compatible name used by existing code and tests.
PaymentProvider = FakePaymentProvider

# Payments that still block a new checkout for the same order.
_BLOCKING_STATUSES = (
    Payment.Status.PROCESSING,
    Payment.Status.SUCCEEDED,
    Payment.Status.REFUNDED,
    Payment.Status.PARTIALLY_REFUNDED,
)


def _can_replace(payment):
    """A failed/cancelled or long-abandoned payment may be retried."""
    if payment.status in (Payment.Status.FAILED, Payment.Status.CANCELLED):
        return True

    if payment.status == Payment.Status.PENDING:
        age = timezone.now() - payment.created_at
        return age > timedelta(minutes=settings.PAYMENT_PENDING_TIMEOUT_MINUTES)

    return False


@transaction.atomic
def initiate_payment(*, user, order_id, provider):
    order = (
        Order.objects
        .select_for_update()
        .filter(id=order_id, user=user)
        .first()
    )

    if not order:
        raise ValueError("Order not found.")

    if order.status == Order.Status.CANCELLED:
        raise ValueError("Cancelled orders cannot be paid.")

    existing = getattr(order, "payment", None)

    if existing is not None:
        if existing.status in _BLOCKING_STATUSES or not _can_replace(existing):
            raise ValueError("This order already has a payment.")

    if order.status != Order.Status.PENDING:
        raise ValueError("This order cannot be paid.")

    provider_result = provider.create_payment(order=order)

    if existing is not None:
        existing.provider = provider.name
        existing.provider_reference = provider_result["provider_reference"]
        existing.amount = order.total
        existing.currency = settings.PAYMENT_CURRENCY
        existing.status = Payment.Status.PENDING
        existing.paid_at = None
        existing.save()
        payment = existing
    else:
        payment = Payment.objects.create(
            order=order,
            provider=provider.name,
            provider_reference=provider_result["provider_reference"],
            amount=order.total,
            currency=settings.PAYMENT_CURRENCY,
            status=Payment.Status.PENDING,
        )

    create_audit_log(
        action="PAYMENT_INITIATED",
        user=user,
        model_name="Payment",
        object_id=payment.id,
        details={
            "order_number": order.order_number,
            "provider": provider.name,
            "amount": str(payment.amount),
        },
    )

    return payment, provider_result


def _mark_succeeded(payment):
    """Shared success path for every provider."""
    if payment.status == Payment.Status.SUCCEEDED:
        return

    payment.status = Payment.Status.SUCCEEDED
    payment.paid_at = timezone.now()
    payment.save(update_fields=["status", "paid_at", "updated_at"])

    order = payment.order

    create_audit_log(
        action="PAYMENT_SUCCEEDED",
        model_name="Payment",
        object_id=payment.id,
        details={
            "order_number": order.order_number,
            "amount": str(payment.amount),
        },
    )

    if order.status == Order.Status.PENDING:
        change_order_status(
            order_id=order.id,
            new_status=Order.Status.CONFIRMED,
            system=True,
        )
        payment.order.refresh_from_db()
    else:
        # The customer paid for an order that was cancelled/expired meanwhile.
        # Stock has been released, so staff must refund it manually.
        create_audit_log(
            action="REFUND_REQUIRED",
            model_name="Order",
            object_id=order.id,
            details={
                "order_number": order.order_number,
                "reason": f"Payment succeeded but order is {order.status}",
                "amount": str(payment.amount),
            },
        )


def _mark_failed(payment):
    if payment.status in (Payment.Status.SUCCEEDED, Payment.Status.FAILED):
        return

    payment.status = Payment.Status.FAILED
    payment.save(update_fields=["status", "updated_at"])

    create_audit_log(
        action="PAYMENT_FAILED",
        model_name="Payment",
        object_id=payment.id,
        details={"order_number": payment.order.order_number},
    )
    notify_payment_failed(payment)


@transaction.atomic
def process_payment_webhook(
    *,
    provider,
    event_id,
    event_type,
    payload,
):
    """
    Generic (test-provider) webhook processor. Real providers are verified and
    translated by their own handler (see ``process_yoco_event``).
    """
    webhook_event, created = WebhookEvent.objects.get_or_create(
        event_id=event_id,
        defaults={
            "provider": provider,
            "event_type": event_type,
            "payload": payload,
        },
    )

    # Idempotency: don't process the same event twice.
    if not created and webhook_event.processed:
        return webhook_event, None

    provider_reference = payload.get("provider_reference")
    payment_status = payload.get("status")

    if not provider_reference:
        raise ValueError("Provider reference is required.")

    payment = (
        Payment.objects
        .select_for_update()
        .select_related("order")
        .filter(
            provider=provider,
            provider_reference=provider_reference,
        )
        .first()
    )

    if not payment:
        raise ValueError("Payment not found.")

    if payment_status == "succeeded":
        _mark_succeeded(payment)

    elif payment_status == "failed":
        _mark_failed(payment)

    else:
        raise ValueError("Unsupported payment status.")

    webhook_event.processed = True
    webhook_event.save(update_fields=["processed"])

    return webhook_event, payment


@transaction.atomic
def process_yoco_event(*, event):
    """
    Handle a signature-verified Yoco event.

    Yoco only sends payment.succeeded, refund.succeeded and refund.failed.
    A failed card attempt simply leaves the checkout unpaid, so the payment
    stays PENDING until it is retried or the unpaid order expires.
    """
    event_id = event.get("id")
    event_type = event.get("type")
    payload = event.get("payload") or {}

    if not event_id or not event_type:
        raise ValueError("Malformed event.")

    webhook_event, created = WebhookEvent.objects.get_or_create(
        event_id=event_id,
        defaults={
            "provider": "yoco",
            "event_type": event_type,
            "payload": event,
        },
    )

    if not created and webhook_event.processed:
        return webhook_event, None

    payment = None

    if event_type == "payment.succeeded":
        checkout_id = (payload.get("metadata") or {}).get("checkoutId")
        if not checkout_id:
            raise ValueError("Event has no checkout reference.")

        payment = (
            Payment.objects
            .select_for_update()
            .select_related("order")
            .filter(provider="yoco", provider_reference=checkout_id)
            .first()
        )

        if not payment:
            raise ValueError("Payment not found.")

        # Never trust the event alone: the paid amount must match the order.
        # (Raised, not logged here: the surrounding transaction rolls back,
        # so the view records the audit entry after the rollback.)
        if payload.get("amount") != to_cents(payment.amount):
            raise PaymentMismatchError(
                "Paid amount does not match the order total.",
                payment_id=payment.id,
                expected=to_cents(payment.amount),
                received=payload.get("amount"),
            )

        if payload.get("currency") != payment.currency:
            raise ValueError("Paid currency does not match the order.")

        _mark_succeeded(payment)

    elif event_type in ("refund.succeeded", "refund.failed"):
        create_audit_log(
            action=event_type.replace(".", "_").upper(),
            model_name="Payment",
            object_id="",
            details={"event_id": event_id},
        )

    # Unknown event types are stored and acknowledged so Yoco stops retrying.
    webhook_event.processed = True
    webhook_event.save(update_fields=["processed"])

    return webhook_event, payment
