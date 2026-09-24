from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class Promotion(models.Model):
    class DiscountType(models.TextChoices):
        PERCENTAGE = "PERCENTAGE", "Percentage"
        FIXED = "FIXED", "Fixed amount"

    name = models.CharField(max_length=150)
    code = models.CharField(max_length=50, unique=True)

    discount_type = models.CharField(
        max_length=20,
        choices=DiscountType.choices,
    )

    discount_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.01)],
    )

    minimum_order_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    starts_at = models.DateTimeField()
    expires_at = models.DateTimeField()

    usage_limit = models.PositiveIntegerField(
        null=True,
        blank=True,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(expires_at__gt=models.F("starts_at")),
                name="promotion_expires_after_start",
            ),
        ]

    def __str__(self):
        return self.code


class CouponRedemption(models.Model):
    promotion = models.ForeignKey(
        Promotion,
        on_delete=models.PROTECT,
        related_name="redemptions",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="coupon_redemptions",
    )

    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="coupon_redemption",
    )

    redeemed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["promotion", "user"],
                name="unique_promotion_redemption_per_user",
            ),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.promotion.code}"
    