from decimal import Decimal

from django.db import transaction
from django.utils.crypto import get_random_string

from cart.models import Cart
from fulfillment.models import Booking, Delivery
from .models import Order, OrderItem


def generate_order_number():
    return f"PB-{get_random_string(10).upper()}"


@transaction.atomic
def create_order(
    user,
    fulfillment_type,
    customer_notes="",
    delivery_data=None,
    scheduled_date=None,
    scheduled_time=None,
):
    cart = (
        Cart.objects
        .select_for_update() # Works like a transaction, the cart is locked during checkout.
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

    delivery_fee = Decimal("0.00")

    if fulfillment_type == Order.FulfillmentType.DELIVERY:
        delivery_fee = Decimal("50.00")

    total = subtotal + delivery_fee

    order = Order.objects.create(
        user=user,
        order_number=generate_order_number(),
        fulfillment_type=fulfillment_type,
        subtotal=subtotal,
        discount_amount=Decimal("0.00"),
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
        if not delivery_data:
            raise ValueError(
                "Delivery information is required."
            )

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

    cart.status = Cart.Status.CONVERTED
    cart.save(update_fields=["status", "updated_at"])

    return order
