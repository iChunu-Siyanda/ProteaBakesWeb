from django.db import transaction

from orders.models import Order, OrderItem

from .models import Review

@transaction.atomic
def create_review(
    *,
    user,
    order_item_id,
    product_id,
    rating,
    comment="",
):
    order_item = (
        OrderItem.objects
        .select_for_update()
        .select_related("order", "product")
        .filter(id=order_item_id)
        .first()
    )

    if not order_item:
        raise ValueError("Order item not found.")

    if order_item.order.user_id != user.id:
        raise ValueError("You cannot review this order item.")

    if order_item.order.status != Order.Status.COMPLETED:
        raise ValueError("Only completed orders can be reviewed.")

    if order_item.product_id != product_id:
        raise ValueError("Product does not match the order item.")

    if Review.objects.filter(order_item=order_item).exists():
        raise ValueError("This order item has already been reviewed.")

    if not 1 <= rating <= 5:
        raise ValueError("Rating must be between 1 and 5.")

    review = Review.objects.create(
        user=user,
        product=order_item.product,
        order_item=order_item,
        rating=rating,
        comment=comment,
    )

    return review