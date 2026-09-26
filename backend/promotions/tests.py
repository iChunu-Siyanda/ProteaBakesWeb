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


from django.contrib.auth import get_user_model
from promotions.services import redeem_promotion, validate_promotion

User = get_user_model()

class PromotionServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="password123",
        )

        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="password123",
        )

        now = timezone.now()

        self.promotion = Promotion.objects.create(
            name="10% Off",
            code="SAVE10",
            discount_type=Promotion.DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            minimum_order_amount=Decimal("100.00"),
            starts_at=now - timedelta(days=1),
            expires_at=now + timedelta(days=1),
            usage_limit=10,
            is_active=True,
        )

        self.order = Order.objects.create(
            user=self.user,
            subtotal=Decimal("200.00"),
            discount_amount=Decimal("0.00"),
            delivery_fee=Decimal("0.00"),
            total=Decimal("200.00"),
        )

    def test_percentage_discount(self):
        promotion, discount = validate_promotion(
            code="SAVE10",
            user=self.user,
            order_total=Decimal("200.00"),
        )

        self.assertEqual(promotion, self.promotion)
        self.assertEqual(discount, Decimal("20.00"))

    def test_fixed_discount(self):
        self.promotion.discount_type = Promotion.DiscountType.FIXED
        self.promotion.discount_value = Decimal("30.00")
        self.promotion.save()

        _, discount = validate_promotion(
            code="SAVE10",
            user=self.user,
            order_total=Decimal("200.00"),
        )

        self.assertEqual(discount, Decimal("30.00"))

    def test_discount_cannot_exceed_order_total(self):
        self.promotion.discount_type = Promotion.DiscountType.FIXED
        self.promotion.discount_value = Decimal("500.00")
        self.promotion.save()

        _, discount = validate_promotion(
            code="SAVE10",
            user=self.user,
            order_total=Decimal("200.00"),
        )

        self.assertEqual(discount, Decimal("200.00"))

    def test_code_is_case_insensitive(self):
        _, discount = validate_promotion(
            code="save10",
            user=self.user,
            order_total=Decimal("200.00"),
        )

        self.assertEqual(discount, Decimal("20.00"))

    def test_inactive_promotion_rejected(self):
        self.promotion.is_active = False
        self.promotion.save()

        with self.assertRaisesMessage(
            ValueError,
            "Promotion not found or inactive.",
        ):
            validate_promotion(
                code="SAVE10",
                user=self.user,
                order_total=Decimal("200.00"),
            )

    def test_promotion_not_started_rejected(self):
        now = timezone.now()

        future_promotion = Promotion.objects.create(
            name="Future Promotion",
            code="FUTURE10",
            discount_type=Promotion.DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            minimum_order_amount=Decimal("100.00"),
            starts_at=now + timedelta(days=1),
            expires_at=now + timedelta(days=2),
            usage_limit=10,
            is_active=True,
        )

        with self.assertRaisesMessage(
            ValueError,
            "Promotion has not started.",
        ):
            validate_promotion(
                code=future_promotion.code,
                user=self.user,
                order_total=Decimal("200.00"),
            )

    def test_expired_promotion_rejected(self):
        self.promotion.expires_at = timezone.now() - timedelta(days=1)
        self.promotion.save()

        with self.assertRaisesMessage(
            ValueError,
            "Promotion has expired.",
        ):
            validate_promotion(
                code="SAVE10",
                user=self.user,
                order_total=Decimal("200.00"),
            )

    def test_minimum_order_amount_rejected(self):
        with self.assertRaisesMessage(
            ValueError,
            "Minimum order amount is 100.00.",
        ):
            validate_promotion(
                code="SAVE10",
                user=self.user,
                order_total=Decimal("50.00"),
            )

    def test_usage_limit_rejected(self):
        self.promotion.usage_limit = 1
        self.promotion.save()

        CouponRedemption.objects.create(
            promotion=self.promotion,
            user=self.other_user,
            order=self.order,
        )

        with self.assertRaisesMessage(
            ValueError,
            "Promotion usage limit has been reached.",
        ):
            validate_promotion(
                code="SAVE10",
                user=self.user,
                order_total=Decimal("200.00"),
            )

    def test_user_cannot_redeem_same_promotion_twice(self):
        CouponRedemption.objects.create(
            promotion=self.promotion,
            user=self.user,
            order=self.order,
        )

        with self.assertRaisesMessage(
            ValueError,
            "You have already used this promotion.",
        ):
            validate_promotion(
                code="SAVE10",
                user=self.user,
                order_total=Decimal("200.00"),
            )

    def test_unknown_promotion_rejected(self):
        with self.assertRaisesMessage(
            ValueError,
            "Promotion not found or inactive.",
        ):
            validate_promotion(
                code="DOESNOTEXIST",
                user=self.user,
                order_total=Decimal("200.00"),
            )

    def test_redeem_promotion_creates_redemption(self):
        redemption = redeem_promotion(
            promotion=self.promotion,
            user=self.user,
            order=self.order,
        )

        self.assertIsNotNone(redemption.pk)
        self.assertEqual(redemption.promotion, self.promotion)
        self.assertEqual(redemption.user, self.user)
        self.assertEqual(redemption.order, self.order)

    def test_redeem_promotion_cannot_be_used_twice_by_same_user(self):
        redeem_promotion(
            promotion=self.promotion,
            user=self.user,
            order=self.order,
        )

        second_order = Order.objects.create(
            order_number="TEST-ORDER-002",
            user=self.user,
            subtotal=Decimal("200.00"),
            discount_amount=Decimal("0.00"),
            delivery_fee=Decimal("0.00"),
            total=Decimal("200.00"),
        )

        with self.assertRaisesMessage(
            ValueError,
            "You have already used this promotion.",
        ):
            redeem_promotion(
                promotion=self.promotion,
                user=self.user,
                order=second_order,
            )

    def test_different_users_can_redeem_same_promotion(self):
        redemption = redeem_promotion(
            promotion=self.promotion,
            user=self.user,
            order=self.order,
        )

        other_order = Order.objects.create(
            order_number="TEST-ORDER-003",
            user=self.other_user,
            subtotal=Decimal("200.00"),
            discount_amount=Decimal("0.00"),
            delivery_fee=Decimal("0.00"),
            total=Decimal("200.00"),
        )

        other_redemption = redeem_promotion(
            promotion=self.promotion,
            user=self.other_user,
            order=other_order,
        )

        self.assertNotEqual(redemption.pk, other_redemption.pk)
        self.assertEqual(
            CouponRedemption.objects.filter(
                promotion=self.promotion,
            ).count(),
            2,
        )


from decimal import Decimal

from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from orders.models import Order
from promotions.models import CouponRedemption, Promotion

User = get_user_model()

class PromotionAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="password123",
        )

        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="password123",
        )

        self.promotion = Promotion.objects.create(
            name="10% Off",
            code="SAVE10",
            discount_type=Promotion.DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            minimum_order_amount=Decimal("100.00"),
            starts_at=self._now_minus_days(1),
            expires_at=self._now_plus_days(1),
            usage_limit=10,
            is_active=True,
        )

        self.order = self._create_order(
            user=self.user,
            order_number="TEST-ORDER-001",
        )

    @staticmethod
    def _now_minus_days(days):
        from datetime import timedelta

        from django.utils import timezone

        return timezone.now() - timedelta(days=days)

    @staticmethod
    def _now_plus_days(days):
        from datetime import timedelta

        from django.utils import timezone

        return timezone.now() + timedelta(days=days)

    def _create_order(
        self,
        *,
        user,
        order_number,
        subtotal=Decimal("200.00"),
        discount_amount=Decimal("0.00"),
        delivery_fee=Decimal("0.00"),
        total=Decimal("200.00"),
        status=Order.Status.PENDING,
    ):
        return Order.objects.create(
            user=user,
            order_number=order_number,
            status=status,
            fulfillment_type=Order.FulfillmentType.PICKUP,
            subtotal=subtotal,
            discount_amount=discount_amount,
            delivery_fee=delivery_fee,
            total=total,
        )

    def test_validate_requires_authentication(self):
        response = self.client.post(
            reverse("promotion-validate"),
            {
                "code": "SAVE10",
                "order_total": "200.00",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_validate_promotion_success(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-validate"),
            {
                "code": "SAVE10",
                "order_total": "200.00",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["promotion"], "SAVE10")
        self.assertEqual(
            Decimal(str(response.data["discount"])),
            Decimal("20.00"),
        )
        self.assertEqual(
            response.data["discount_type"],
            Promotion.DiscountType.PERCENTAGE,
        )

    def test_validate_fixed_discount(self):
        self.promotion.discount_type = Promotion.DiscountType.FIXED
        self.promotion.discount_value = Decimal("30.00")
        self.promotion.save()

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-validate"),
            {
                "code": "SAVE10",
                "order_total": "200.00",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            Decimal(str(response.data["discount"])),
            Decimal("30.00"),
        )

    def test_validate_case_insensitive_code(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-validate"),
            {
                "code": "save10",
                "order_total": "200.00",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["promotion"], "SAVE10")

    def test_validate_unknown_promotion(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-validate"),
            {
                "code": "INVALID",
                "order_total": "200.00",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "Promotion not found or inactive.",
        )

    def test_validate_inactive_promotion(self):
        self.promotion.is_active = False
        self.promotion.save()

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-validate"),
            {
                "code": "SAVE10",
                "order_total": "200.00",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "Promotion not found or inactive.",
        )

    def test_validate_expired_promotion(self):
        from datetime import timedelta

        from django.utils import timezone

        self.promotion.starts_at = timezone.now() - timedelta(days=2)
        self.promotion.expires_at = timezone.now() - timedelta(days=1)
        self.promotion.save()

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-validate"),
            {
                "code": "SAVE10",
                "order_total": "200.00",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "Promotion has expired.",
        )

    def test_validate_promotion_not_started(self):
        from datetime import timedelta

        from django.utils import timezone

        now = timezone.now()

        future_promotion = Promotion.objects.create(
            name="Future Promotion",
            code="FUTURE10",
            discount_type=Promotion.DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            minimum_order_amount=Decimal("100.00"),
            starts_at=now + timedelta(days=1),
            expires_at=now + timedelta(days=2),
            usage_limit=10,
            is_active=True,
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-validate"),
            {
                "code": future_promotion.code,
                "order_total": "200.00",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "Promotion has not started.",
        )

    def test_validate_minimum_order_amount(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-validate"),
            {
                "code": "SAVE10",
                "order_total": "50.00",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "Minimum order amount is 100.00.",
        )

    def test_validate_usage_limit_reached(self):
        self.promotion.usage_limit = 1
        self.promotion.save()

        self._create_order(
            user=self.other_user,
            order_number="TEST-ORDER-002",
        )

        CouponRedemption.objects.create(
            promotion=self.promotion,
            user=self.other_user,
            order=Order.objects.get(
                order_number="TEST-ORDER-002",
            ),
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-validate"),
            {
                "code": "SAVE10",
                "order_total": "200.00",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "Promotion usage limit has been reached.",
        )

    def test_validate_same_user_redemption_rejected(self):
        CouponRedemption.objects.create(
            promotion=self.promotion,
            user=self.user,
            order=self.order,
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-validate"),
            {
                "code": "SAVE10",
                "order_total": "200.00",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "You have already used this promotion.",
        )

    def test_validate_missing_code(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-validate"),
            {
                "order_total": "200.00",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", response.data)

    def test_validate_missing_order_total(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-validate"),
            {
                "code": "SAVE10",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("order_total", response.data)

    def test_validate_invalid_order_total(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-validate"),
            {
                "code": "SAVE10",
                "order_total": "-50.00",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("order_total", response.data)

    def test_redeem_requires_authentication(self):
        response = self.client.post(
            reverse("promotion-redeem"),
            {
                "code": "SAVE10",
                "order_id": self.order.id,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_redeem_promotion_success(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-redeem"),
            {
                "code": "SAVE10",
                "order_id": self.order.id,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["promotion"], "SAVE10")
        self.assertEqual(
            Decimal(str(response.data["discount"])),
            Decimal("20.00"),
        )
        self.assertIn("redemption_id", response.data)

        self.assertTrue(
            CouponRedemption.objects.filter(
                promotion=self.promotion,
                user=self.user,
                order=self.order,
            ).exists()
        )

    def test_redeem_other_users_order_rejected(self):
        other_order = self._create_order(
            user=self.other_user,
            order_number="TEST-ORDER-002",
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-redeem"),
            {
                "code": "SAVE10",
                "order_id": other_order.id,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_redeem_nonexistent_order(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-redeem"),
            {
                "code": "SAVE10",
                "order_id": 999999,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(
            response.data["detail"],
            "Order not found.",
        )

    def test_redeem_unknown_promotion(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-redeem"),
            {
                "code": "INVALID",
                "order_id": self.order.id,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "Promotion not found or inactive.",
        )

    def test_redeem_inactive_promotion(self):
        self.promotion.is_active = False
        self.promotion.save()

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-redeem"),
            {
                "code": "SAVE10",
                "order_id": self.order.id,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_redeem_below_minimum_order_amount(self):
        low_value_order = self._create_order(
            user=self.user,
            order_number="TEST-ORDER-002",
            subtotal=Decimal("50.00"),
            total=Decimal("50.00"),
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-redeem"),
            {
                "code": "SAVE10",
                "order_id": low_value_order.id,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "Minimum order amount is 100.00.",
        )

    def test_redeem_same_promotion_twice_rejected(self):
        CouponRedemption.objects.create(
            promotion=self.promotion,
            user=self.user,
            order=self.order,
        )

        second_order = self._create_order(
            user=self.user,
            order_number="TEST-ORDER-002",
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-redeem"),
            {
                "code": "SAVE10",
                "order_id": second_order.id,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "You have already used this promotion.",
        )

    def test_redeem_usage_limit_reached(self):
        self.promotion.usage_limit = 1
        self.promotion.save()

        other_order = self._create_order(
            user=self.other_user,
            order_number="TEST-ORDER-002",
        )

        CouponRedemption.objects.create(
            promotion=self.promotion,
            user=self.other_user,
            order=other_order,
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-redeem"),
            {
                "code": "SAVE10",
                "order_id": self.order.id,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "Promotion usage limit has been reached.",
        )

    def test_redeem_missing_code(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-redeem"),
            {
                "order_id": self.order.id,
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("code", response.data)

    def test_redeem_missing_order_id(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-redeem"),
            {
                "code": "SAVE10",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("order_id", response.data)

    def test_redeem_invalid_order_id(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-redeem"),
            {
                "code": "SAVE10",
                "order_id": "invalid",
            },
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("order_id", response.data)

