from django.conf import settings
from django.db import transaction

from orders.models import Order

from .models import Payment


class PaymentProvider:
    """
    Provider interface.

    A real payment provider implementation will eventually
    replace this class.
    """

    name = "test"

    def create_payment(self, *, order):
        return {
            "provider_reference": f"TEST-{order.order_number}",
            "checkout_url": f"https://example.com/pay/{order.order_number}",
        }


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

    if hasattr(order, "payment"):
        raise ValueError("This order already has a payment.")

    if order.status == Order.Status.CANCELLED:
        raise ValueError("Cancelled orders cannot be paid.")

    provider_result = provider.create_payment(order=order)

    payment = Payment.objects.create(
        order=order,
        provider=provider.name,
        provider_reference=provider_result["provider_reference"],
        amount=order.total,
        currency=settings.PAYMENT_CURRENCY,
        status=Payment.Status.PENDING,
    )

    return payment, provider_result


from django.utils import timezone

from .models import Payment, WebhookEvent


@transaction.atomic
def process_payment_webhook(
    *,
    provider,
    event_id,
    event_type,
    payload,
):
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
        .filter(
            provider=provider,
            provider_reference=provider_reference,
        )
        .first()
    )

    if not payment:
        raise ValueError("Payment not found.")

    if payment_status == "succeeded":
        payment.status = Payment.Status.SUCCEEDED
        payment.paid_at = timezone.now()
        payment.save(update_fields=["status", "paid_at", "updated_at"])

        payment.order.status = payment.order.Status.CONFIRMED
        payment.order.save(update_fields=["status", "updated_at"])

    elif payment_status == "failed":
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status", "updated_at"])

    else:
        raise ValueError("Unsupported payment status.")

    webhook_event.processed = True
    webhook_event.save(update_fields=["processed"])

    return webhook_event, payment
