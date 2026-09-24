from decimal import Decimal
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone

from orders.models import Order
from promotions.models import CouponRedemption, Promotion
from users.models import User


class PromotionModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="customer@example.com",
            password="securepassword123",
            first_name="John",
            last_name="Doe",
        )

        now = timezone.now()

        self.promotion = Promotion.objects.create(
            name="Summer Sale",
            code="SUMMER10",
            discount_type=Promotion.DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            minimum_order_amount=Decimal("100.00"),
            starts_at=now,
            expires_at=now + timedelta(days=30),
        )

        self.order = Order.objects.create(
            user=self.user,
            order_number="PB-000001",
            fulfillment_type=Order.FulfillmentType.PICKUP,
            subtotal=Decimal("250.00"),
            discount_amount=Decimal("25.00"),
            delivery_fee=Decimal("0.00"),
            total=Decimal("225.00"),
        )

    def test_discount_value_must_be_positive(self):
        promotion = Promotion(
            name="Invalid Promotion",
            code="INVALID",
            discount_type=Promotion.DiscountType.PERCENTAGE,
            discount_value=Decimal("0.00"),
            starts_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=1),
        )

        with self.assertRaises(ValidationError):
            promotion.full_clean()

    def test_promotion_expiry_must_be_after_start(self):
        now = timezone.now()

        promotion = Promotion(
            name="Invalid Dates",
            code="INVALID-DATES",
            discount_type=Promotion.DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            starts_at=now,
            expires_at=now - timedelta(days=1),
        )

        with self.assertRaises(ValidationError):
            promotion.full_clean()

    def test_user_cannot_redeem_same_promotion_twice(self):
        CouponRedemption.objects.create(
            promotion=self.promotion,
            user=self.user,
            order=self.order,
        )

        second_order = Order.objects.create(
            user=self.user,
            order_number="PB-000002",
            fulfillment_type=Order.FulfillmentType.PICKUP,
            subtotal=Decimal("250.00"),
            discount_amount=Decimal("25.00"),
            delivery_fee=Decimal("0.00"),
            total=Decimal("225.00"),
        )

        with self.assertRaises(IntegrityError):
            CouponRedemption.objects.create(
                promotion=self.promotion,
                user=self.user,
                order=second_order,
            )
            