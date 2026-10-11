from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.crypto import get_random_string

from audit.services import create_audit_log
from cart.models import Cart
from fulfillment.models import Booking, Delivery
from inventory.services import release_stock_for_order, reserve_stock_for_order
from notifications.events import notify_order_status
from promotions.models import CouponRedemption
from promotions.services import redeem_promotion, validate_promotion

from .models import Order, OrderItem, OrderStatusHistory


def generate_order_number():
    return f"PB-{get_random_string(10).upper()}"


def calculate_delivery_fee(*, fulfillment_type, subtotal_after_discount):
    if fulfillment_type != Order.FulfillmentType.DELIVERY:
        return Decimal("0.00")

    threshold = settings.FREE_DELIVERY_THRESHOLD
    if threshold is not None and subtotal_after_discount >= threshold:
        return Decimal("0.00")

    return settings.DELIVERY_FEE


@transaction.atomic
def create_order(
    user,
    fulfillment_type,
    customer_notes="",
    delivery_data=None,
    scheduled_date=None,
    scheduled_time=None,
    promotion_code=None,
):
    cart = (
        Cart.objects
        .select_for_update()  # the cart is locked for the duration of checkout
        .prefetch_related("items__product")
        .filter(
            user=user,
            status=Cart.Status.ACTIVE,
        )
        .first()
    )

    if not cart or not cart.items.exists():
        raise ValueError("Your cart is empty.")

    items = list(cart.items.all())

    subtotal = Decimal("0.00")

    for item in items:
        if not item.product.is_active:
            raise ValueError(
                f"{item.product.name} is no longer available."
            )

        subtotal += item.product.price * item.quantity

    if fulfillment_type == Order.FulfillmentType.DELIVERY and not delivery_data:
        raise ValueError("Delivery information is required.")

    if (
        fulfillment_type == Order.FulfillmentType.PICKUP
        and settings.PICKUP_MAX_BOOKINGS_PER_DAY
        and scheduled_date
    ):
        booked = (
            Booking.objects
            .filter(scheduled_date=scheduled_date)
            .exclude(status=Booking.Status.CANCELLED)
            .count()
        )
        if booked >= settings.PICKUP_MAX_BOOKINGS_PER_DAY:
            raise ValueError(
                "We're fully booked for that day. Please choose another date."
            )

    promotion = None
    discount = Decimal("0.00")

    if promotion_code:
        promotion, discount = validate_promotion(
            code=promotion_code,
            user=user,
            order_total=subtotal,
        )
        discount = discount.quantize(Decimal("0.01"))

    delivery_fee = calculate_delivery_fee(
        fulfillment_type=fulfillment_type,
        subtotal_after_discount=subtotal - discount,
    )

    total = subtotal - discount + delivery_fee

    order = Order.objects.create(
        user=user,
        order_number=generate_order_number(),
        fulfillment_type=fulfillment_type,
        subtotal=subtotal,
        discount_amount=discount,
        delivery_fee=delivery_fee,
        total=total,
        customer_notes=customer_notes,
    )

    OrderItem.objects.bulk_create(
        [
            OrderItem(
                order=order,
                product=item.product,
                product_name=item.product.name,
                unit_price=item.product.price,
                quantity=item.quantity,
                subtotal=item.product.price * item.quantity,
            )
            for item in items
        ]
    )

    if fulfillment_type == Order.FulfillmentType.PICKUP:
        Booking.objects.create(
            order=order,
            scheduled_date=scheduled_date,
            scheduled_time=scheduled_time,
        )

    elif fulfillment_type == Order.FulfillmentType.DELIVERY:
        Delivery.objects.create(
            order=order,
            recipient_name=delivery_data["recipient_name"],
            recipient_phone=delivery_data["phone_number"],
            address_line_1=delivery_data["address_line_1"],
            address_line_2=delivery_data.get("address_line_2", ""),
            city=delivery_data["city"],
            province=delivery_data["province"],
            postal_code=delivery_data["postal_code"],
            delivery_fee=delivery_fee,
        )

    # Deduct stock for tracked products; raises ValueError if short.
    reserve_stock_for_order(order)

    if promotion:
        redeem_promotion(promotion=promotion, user=user, order=order)

    cart.status = Cart.Status.CONVERTED
    cart.save(update_fields=["status", "updated_at"])

    create_audit_log(
        action="ORDER_CREATED",
        user=user,
        model_name="Order",
        object_id=order.id,
        details={
            "order_number": order.order_number,
            "total": str(order.total),
            "promotion": promotion.code if promotion else None,
        },
    )

    return order


# ---------------------------------------------------------------------------
# Status lifecycle
# ---------------------------------------------------------------------------

S = Order.Status

# Transitions staff may perform. PENDING -> CONFIRMED is system-only (payment).
STAFF_TRANSITIONS = {
    S.PENDING: {S.CANCELLED},
    S.CONFIRMED: {S.PREPARING, S.CANCELLED},
    S.PREPARING: {S.READY, S.CANCELLED},
    S.READY: {S.COMPLETED, S.OUT_FOR_DELIVERY, S.CANCELLED},
    S.OUT_FOR_DELIVERY: {S.COMPLETED},
    S.COMPLETED: set(),
    S.CANCELLED: set(),
}
SYSTEM_TRANSITIONS = {(S.PENDING, S.CONFIRMED)}


def _sync_fulfillment(order):
    booking = getattr(order, "booking", None)
    delivery = getattr(order, "delivery", None)

    if booking is not None:
        mapping = {
            S.CONFIRMED: Booking.Status.CONFIRMED,
            S.COMPLETED: Booking.Status.COMPLETED,
            S.CANCELLED: Booking.Status.CANCELLED,
        }
        new_status = mapping.get(order.status)
        if new_status and booking.status != new_status:
            booking.status = new_status
            booking.save(update_fields=["status", "updated_at"])

    if delivery is not None:
        mapping = {
            S.OUT_FOR_DELIVERY: Delivery.Status.OUT_FOR_DELIVERY,
            S.COMPLETED: Delivery.Status.DELIVERED,
            S.CANCELLED: Delivery.Status.CANCELLED,
        }
        new_status = mapping.get(order.status)
        if new_status and delivery.status != new_status:
            delivery.status = new_status
            update_fields = ["status", "updated_at"]
            if new_status == Delivery.Status.DELIVERED:
                delivery.delivered_at = timezone.now()
                update_fields.append("delivered_at")
            delivery.save(update_fields=update_fields)


def _release_order_resources(order):
    """Cancelled orders give back stock and their coupon."""
    release_stock_for_order(order)
    CouponRedemption.objects.filter(order=order).delete()

    payment = getattr(order, "payment", None)
    if payment is not None:
        from payments.models import Payment

        if payment.status in (Payment.Status.PENDING, Payment.Status.PROCESSING):
            payment.status = Payment.Status.CANCELLED
            payment.save(update_fields=["status", "updated_at"])
        elif payment.status == Payment.Status.SUCCEEDED:
            create_audit_log(
                action="REFUND_REQUIRED",
                model_name="Order",
                object_id=order.id,
                details={
                    "order_number": order.order_number,
                    "amount": str(payment.amount),
                },
            )


@transaction.atomic
def change_order_status(*, order_id, new_status, changed_by=None, system=False):
    order = (
        Order.objects
        .select_for_update()
        .select_related("user")
        .get(pk=order_id)
    )

    old_status = order.status

    if old_status == new_status:
        raise ValueError(f"Order is already {new_status}.")

    allowed = new_status in STAFF_TRANSITIONS.get(old_status, set()) or (
        system and (old_status, new_status) in SYSTEM_TRANSITIONS
    )
    if not allowed:
        raise ValueError(
            f"An order cannot move from {old_status} to {new_status}."
        )

    if new_status == S.OUT_FOR_DELIVERY and (
        order.fulfillment_type != Order.FulfillmentType.DELIVERY
    ):
        raise ValueError("Only delivery orders can be sent out for delivery.")

    if (
        old_status == S.READY
        and new_status == S.COMPLETED
        and order.fulfillment_type == Order.FulfillmentType.DELIVERY
    ):
        raise ValueError("Delivery orders must go out for delivery first.")

    order.status = new_status
    order.save(update_fields=["status", "updated_at"])

    OrderStatusHistory.objects.create(
        order=order,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
    )

    _sync_fulfillment(order)

    if new_status == S.CANCELLED:
        _release_order_resources(order)

    create_audit_log(
        action="ORDER_STATUS_CHANGED",
        user=changed_by,
        model_name="Order",
        object_id=order.id,
        details={"old": old_status, "new": new_status},
    )

    notify_order_status(order)

    return order


def cancel_order_for_customer(*, user, order_number):
    """Customers may only cancel orders that are still unpaid."""
    order = Order.objects.filter(user=user, order_number=order_number).first()

    if not order:
        raise LookupError("Order not found.")

    if order.status != S.PENDING:
        raise ValueError(
            "This order can no longer be cancelled online. Please contact us."
        )

    payment = getattr(order, "payment", None)
    if payment is not None and payment.status == "SUCCEEDED":
        raise ValueError(
            "This order has been paid. Please contact us to cancel it."
        )

    return change_order_status(
        order_id=order.id,
        new_status=S.CANCELLED,
        changed_by=user,
    )


def expire_unpaid_orders(*, now=None):
    """Cancel PENDING orders that were never paid. Returns the number cancelled."""
    now = now or timezone.now()
    cutoff = now - timedelta(minutes=settings.UNPAID_ORDER_EXPIRY_MINUTES)

    stale = Order.objects.filter(
        status=S.PENDING,
        created_at__lt=cutoff,
    ).exclude(payment__status="SUCCEEDED")

    count = 0
    for order_id in stale.values_list("id", flat=True):
        try:
            change_order_status(order_id=order_id, new_status=S.CANCELLED)
            count += 1
        except ValueError:
            continue

    return count
