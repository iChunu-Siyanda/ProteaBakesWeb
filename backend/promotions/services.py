from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from .models import CouponRedemption, Promotion


def validate_promotion(*, code, user, order_total):
    promotion = (
        Promotion.objects
        .filter(
            code__iexact=code,
            is_active=True,
        )
        .first()
    )

    if not promotion:
        raise ValueError("Promotion not found or inactive.")

    now = timezone.now()

    if now < promotion.starts_at:
        raise ValueError("Promotion has not started.")

    if now > promotion.expires_at:
        raise ValueError("Promotion has expired.")

    if order_total < promotion.minimum_order_amount:
        raise ValueError(
            f"Minimum order amount is {promotion.minimum_order_amount}."
        )

    if (
        promotion.usage_limit is not None
        and promotion.redemptions.count() >= promotion.usage_limit
    ):
        raise ValueError("Promotion usage limit has been reached.")

    if CouponRedemption.objects.filter(
        promotion=promotion,
        user=user,
    ).exists():
        raise ValueError("You have already used this promotion.")

    if promotion.discount_type == Promotion.DiscountType.PERCENTAGE:
        discount = (
            order_total
            * promotion.discount_value
            / Decimal("100")
        )
    else:
        discount = promotion.discount_value

    discount = min(discount, order_total)

    return promotion, discount


@transaction.atomic
def redeem_promotion(*, promotion, user, order, discount=None):
    """
    Record a redemption. When ``discount`` is given and the order is still an
    unpaid PENDING order that has no discount yet, the discount is also applied
    to the order's totals so the customer actually pays the reduced price.
    """
    if CouponRedemption.objects.filter(
        promotion=promotion,
        user=user,
    ).exists():
        raise ValueError("You have already used this promotion.")

    if CouponRedemption.objects.filter(order=order).exists():
        raise ValueError("This order already has a promotion applied.")

    redemption = CouponRedemption.objects.create(
        promotion=promotion,
        user=user,
        order=order,
    )

    if (
        discount
        and order.status == "PENDING"
        and not hasattr(order, "payment")
        and not order.discount_amount
    ):
        discount = Decimal(discount).quantize(Decimal("0.01"))
        order.discount_amount = discount
        order.total = max(
            order.subtotal - discount + order.delivery_fee,
            Decimal("0.00"),
        )
        order.save(update_fields=["discount_amount", "total", "updated_at"])

    return redemption
