from datetime import date, time, timedelta
from decimal import Decimal

from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditLog
from cart.models import Cart, CartItem
from catalog.models import Category, Product
from fulfillment.models import Booking, Delivery
from inventory.models import InventoryItem, InventoryMovement
from notifications.models import Notification
from orders.models import Order, OrderStatusHistory
from orders.services import change_order_status, create_order, expire_unpaid_orders
from payments.models import Payment
from promotions.models import CouponRedemption, Promotion
from users.models import User

from .tests import PICKUP_DATE

DELIVERY = {
    "recipient_name": "Jane Doe",
    "phone_number": "0821234567",
    "address_line_1": "1 Protea Street",
    "city": "Welkom",
    "province": "Free State",
    "postal_code": "9459",
}


class Fixture:
    def make_fixture(self):
        self.user = User.objects.create_user(
            email="customer@example.com",
            password="securepassword123",
            first_name="Jane",
            last_name="Doe",
        )
        self.staff = User.objects.create_user(
            email="staff@example.com",
            password="securepassword123",
            is_staff=True,
        )
        self.category = Category.objects.create(name="Cakes", slug="cakes")
        self.product = Product.objects.create(
            category=self.category,
            name="Chocolate Cake",
            slug="chocolate-cake",
            price=Decimal("250.00"),
            sku="CAKE-001",
        )

    def fill_cart(self, user=None, product=None, quantity=2):
        cart = Cart.objects.create(user=user or self.user)
        CartItem.objects.create(
            cart=cart, product=product or self.product, quantity=quantity
        )
        return cart

    def pickup_order(self, **kwargs):
        self.fill_cart()
        return create_order(
            user=self.user,
            fulfillment_type=Order.FulfillmentType.PICKUP,
            scheduled_date=date.fromisoformat(PICKUP_DATE),
            scheduled_time=time(10, 0),
            **kwargs,
        )

    def delivery_order(self):
        self.fill_cart()
        return create_order(
            user=self.user,
            fulfillment_type=Order.FulfillmentType.DELIVERY,
            delivery_data=DELIVERY,
        )


class CheckoutRuleTests(Fixture, TestCase):
    def setUp(self):
        self.make_fixture()

    def test_delivery_fee_comes_from_settings(self):
        with override_settings(DELIVERY_FEE=Decimal("75.00")):
            order = self.delivery_order()

        self.assertEqual(order.delivery_fee, Decimal("75.00"))
        self.assertEqual(order.total, Decimal("575.00"))

    def test_free_delivery_threshold(self):
        with override_settings(FREE_DELIVERY_THRESHOLD=Decimal("400.00")):
            order = self.delivery_order()

        self.assertEqual(order.delivery_fee, Decimal("0.00"))
        self.assertEqual(order.total, Decimal("500.00"))

    def test_promotion_is_applied_at_checkout(self):
        Promotion.objects.create(
            name="Ten percent",
            code="SAVE10",
            discount_type=Promotion.DiscountType.PERCENTAGE,
            discount_value=Decimal("10.00"),
            starts_at=timezone.now() - timedelta(days=1),
            expires_at=timezone.now() + timedelta(days=1),
        )

        order = self.pickup_order(promotion_code="save10")

        self.assertEqual(order.subtotal, Decimal("500.00"))
        self.assertEqual(order.discount_amount, Decimal("50.00"))
        self.assertEqual(order.total, Decimal("450.00"))
        self.assertTrue(CouponRedemption.objects.filter(order=order).exists())

    def test_invalid_promotion_blocks_checkout_and_keeps_cart(self):
        cart = self.fill_cart()

        with self.assertRaises(ValueError):
            create_order(
                user=self.user,
                fulfillment_type=Order.FulfillmentType.PICKUP,
                scheduled_date=date.fromisoformat(PICKUP_DATE),
                scheduled_time=time(10, 0),
                promotion_code="NOPE",
            )

        cart.refresh_from_db()
        self.assertEqual(cart.status, Cart.Status.ACTIVE)
        self.assertFalse(Order.objects.exists())

    @override_settings(PICKUP_MAX_BOOKINGS_PER_DAY=1)
    def test_daily_pickup_capacity(self):
        self.pickup_order()
        self.fill_cart()

        with self.assertRaisesMessage(ValueError, "fully booked"):
            create_order(
                user=self.user,
                fulfillment_type=Order.FulfillmentType.PICKUP,
                scheduled_date=date.fromisoformat(PICKUP_DATE),
                scheduled_time=time(11, 0),
            )

    def test_checkout_writes_audit_log(self):
        order = self.pickup_order()

        self.assertTrue(
            AuditLog.objects.filter(
                action="ORDER_CREATED", object_id=str(order.id)
            ).exists()
        )


class InventoryIntegrationTests(Fixture, APITestCase):
    def setUp(self):
        self.make_fixture()
        self.stock = InventoryItem.objects.create(product=self.product, quantity=5)

    def test_checkout_reserves_stock(self):
        order = self.pickup_order()

        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 3)
        self.assertTrue(
            InventoryMovement.objects.filter(
                reference=order.order_number, movement_type="SALE", quantity=2
            ).exists()
        )

    def test_checkout_rejected_when_not_enough_stock(self):
        self.stock.quantity = 1
        self.stock.save()
        self.fill_cart(quantity=2)

        with self.assertRaises(ValueError):
            create_order(
                user=self.user,
                fulfillment_type=Order.FulfillmentType.PICKUP,
                scheduled_date=date.fromisoformat(PICKUP_DATE),
                scheduled_time=time(10, 0),
            )

        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 1)
        self.assertFalse(Order.objects.exists())

    def test_cancelling_returns_stock_once(self):
        order = self.pickup_order()

        change_order_status(order_id=order.id, new_status="CANCELLED", changed_by=self.staff)

        self.stock.refresh_from_db()
        self.assertEqual(self.stock.quantity, 5)
        self.assertEqual(
            InventoryMovement.objects.filter(
                reference=order.order_number, movement_type="RETURN"
            ).count(),
            1,
        )

    def test_made_to_order_products_ignore_stock(self):
        self.product.is_made_to_order = True
        self.product.save()
        self.stock.quantity = 0
        self.stock.save()

        order = self.pickup_order()

        self.assertEqual(order.status, Order.Status.PENDING)

    def test_cannot_add_more_than_stock_to_cart(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("cart-item-create"),
            {"product": self.product.id, "quantity": 6},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class StatusLifecycleTests(Fixture, TestCase):
    def setUp(self):
        self.make_fixture()

    def test_pickup_happy_path_syncs_booking_and_logs_history(self):
        order = self.pickup_order()

        # Payment confirmation is a system transition.
        change_order_status(order_id=order.id, new_status="CONFIRMED", system=True)
        for new_status in ("PREPARING", "READY", "COMPLETED"):
            order = change_order_status(
                order_id=order.id, new_status=new_status, changed_by=self.staff
            )

        self.assertEqual(order.status, Order.Status.COMPLETED)
        self.assertEqual(order.booking.status, Booking.Status.COMPLETED)
        self.assertEqual(OrderStatusHistory.objects.filter(order=order).count(), 4)

    def test_staff_cannot_confirm_unpaid_order(self):
        order = self.pickup_order()

        with self.assertRaises(ValueError):
            change_order_status(
                order_id=order.id, new_status="CONFIRMED", changed_by=self.staff
            )

    def test_cannot_skip_steps(self):
        order = self.pickup_order()
        change_order_status(order_id=order.id, new_status="CONFIRMED", system=True)

        with self.assertRaises(ValueError):
            change_order_status(order_id=order.id, new_status="COMPLETED")

    def test_delivery_flow_marks_delivery_delivered(self):
        order = self.delivery_order()
        change_order_status(order_id=order.id, new_status="CONFIRMED", system=True)
        for new_status in ("PREPARING", "READY", "OUT_FOR_DELIVERY"):
            order = change_order_status(order_id=order.id, new_status=new_status)

        self.assertEqual(order.delivery.status, Delivery.Status.OUT_FOR_DELIVERY)

        order = change_order_status(order_id=order.id, new_status="COMPLETED")

        self.assertEqual(order.delivery.status, Delivery.Status.DELIVERED)
        self.assertIsNotNone(order.delivery.delivered_at)

    def test_pickup_order_cannot_go_out_for_delivery(self):
        order = self.pickup_order()
        change_order_status(order_id=order.id, new_status="CONFIRMED", system=True)
        change_order_status(order_id=order.id, new_status="PREPARING")
        change_order_status(order_id=order.id, new_status="READY")

        with self.assertRaises(ValueError):
            change_order_status(order_id=order.id, new_status="OUT_FOR_DELIVERY")

    def test_delivery_order_cannot_skip_delivery_step(self):
        order = self.delivery_order()
        change_order_status(order_id=order.id, new_status="CONFIRMED", system=True)
        change_order_status(order_id=order.id, new_status="PREPARING")
        change_order_status(order_id=order.id, new_status="READY")

        with self.assertRaises(ValueError):
            change_order_status(order_id=order.id, new_status="COMPLETED")

    def test_status_change_notifies_customer_and_emails(self):
        order = self.pickup_order()

        with self.captureOnCommitCallbacks(execute=True):
            change_order_status(order_id=order.id, new_status="CONFIRMED", system=True)

        self.assertTrue(
            Notification.objects.filter(
                user=self.user, notification_type="ORDER_CONFIRMED"
            ).exists()
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [self.user.email])

    def test_email_is_skipped_when_customer_disabled_it(self):
        from notifications.models import NotificationPreference

        NotificationPreference.objects.create(user=self.user, email_enabled=False)
        order = self.pickup_order()

        with self.captureOnCommitCallbacks(execute=True):
            change_order_status(order_id=order.id, new_status="CONFIRMED", system=True)

        self.assertEqual(len(mail.outbox), 0)
        self.assertTrue(Notification.objects.filter(user=self.user).exists())

    def test_cancelling_releases_coupon_and_flags_paid_refund(self):
        promo = Promotion.objects.create(
            name="Fixed",
            code="R50",
            discount_type=Promotion.DiscountType.FIXED,
            discount_value=Decimal("50.00"),
            starts_at=timezone.now() - timedelta(days=1),
            expires_at=timezone.now() + timedelta(days=1),
        )
        order = self.pickup_order(promotion_code="R50")
        Payment.objects.create(
            order=order,
            provider="test",
            provider_reference="TEST-X",
            amount=order.total,
            currency="ZAR",
            status=Payment.Status.SUCCEEDED,
        )
        change_order_status(order_id=order.id, new_status="CONFIRMED", system=True)

        change_order_status(order_id=order.id, new_status="CANCELLED")

        self.assertFalse(CouponRedemption.objects.filter(promotion=promo).exists())
        self.assertTrue(AuditLog.objects.filter(action="REFUND_REQUIRED").exists())


class ExpiryTests(Fixture, TestCase):
    def setUp(self):
        self.make_fixture()

    @override_settings(UNPAID_ORDER_EXPIRY_MINUTES=60)
    def test_old_unpaid_orders_are_cancelled_and_new_ones_kept(self):
        old = self.pickup_order()
        Order.objects.filter(pk=old.pk).update(
            created_at=timezone.now() - timedelta(hours=3)
        )
        self.fill_cart()
        fresh = create_order(
            user=self.user,
            fulfillment_type=Order.FulfillmentType.PICKUP,
            scheduled_date=date.fromisoformat(PICKUP_DATE),
            scheduled_time=time(10, 0),
        )

        self.assertEqual(expire_unpaid_orders(), 1)

        old.refresh_from_db()
        fresh.refresh_from_db()
        self.assertEqual(old.status, Order.Status.CANCELLED)
        self.assertEqual(fresh.status, Order.Status.PENDING)

    def test_paid_orders_never_expire(self):
        order = self.pickup_order()
        Payment.objects.create(
            order=order,
            provider="test",
            provider_reference="TEST-PAID",
            amount=order.total,
            currency="ZAR",
            status=Payment.Status.SUCCEEDED,
        )
        Order.objects.filter(pk=order.pk).update(
            created_at=timezone.now() - timedelta(days=2)
        )

        self.assertEqual(expire_unpaid_orders(), 0)

    def test_management_command_runs(self):
        call_command("expire_unpaid_orders")


class OrderAPITests(Fixture, APITestCase):
    def setUp(self):
        self.make_fixture()
        self.other = User.objects.create_user(
            email="other@example.com", password="securepassword123"
        )

    def test_orders_require_authentication(self):
        for name in ("order-list", "staff-order-list"):
            response = self.client.get(reverse(name))
            self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_customer_lists_only_own_orders_paginated(self):
        mine = self.pickup_order()
        self.fill_cart(user=self.other)
        create_order(
            user=self.other,
            fulfillment_type=Order.FulfillmentType.DELIVERY,
            delivery_data=DELIVERY,
        )

        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse("order-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["order_number"], mine.order_number)

    def test_order_detail_includes_fulfillment_and_payment(self):
        order = self.pickup_order()
        self.client.force_authenticate(user=self.user)

        response = self.client.get(
            reverse("order-detail", kwargs={"order_number": order.order_number})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["fulfillment"]["type"], "PICKUP")
        self.assertIsNone(response.data["payment"])

    def test_cannot_view_another_customers_order(self):
        order = self.pickup_order()
        self.client.force_authenticate(user=self.other)

        response = self.client.get(
            reverse("order-detail", kwargs={"order_number": order.order_number})
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_customer_can_cancel_unpaid_order(self):
        order = self.pickup_order()
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("order-cancel", kwargs={"order_number": order.order_number})
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "CANCELLED")

    def test_customer_cannot_cancel_confirmed_order(self):
        order = self.pickup_order()
        change_order_status(order_id=order.id, new_status="CONFIRMED", system=True)
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("order-cancel", kwargs={"order_number": order.order_number})
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_customer_cannot_cancel_someone_elses_order(self):
        order = self.pickup_order()
        self.client.force_authenticate(user=self.other)

        response = self.client.post(
            reverse("order-cancel", kwargs={"order_number": order.order_number})
        )

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_customer_cannot_change_status(self):
        order = self.pickup_order()
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("staff-order-status", kwargs={"order_number": order.order_number}),
            {"status": "PREPARING"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_advance_status(self):
        order = self.pickup_order()
        change_order_status(order_id=order.id, new_status="CONFIRMED", system=True)
        self.client.force_authenticate(user=self.staff)

        response = self.client.post(
            reverse("staff-order-status", kwargs={"order_number": order.order_number}),
            {"status": "PREPARING"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "PREPARING")
        self.assertEqual(response.data["customer_email"], "customer@example.com")

    def test_staff_invalid_transition_is_400(self):
        order = self.pickup_order()
        self.client.force_authenticate(user=self.staff)

        response = self.client.post(
            reverse("staff-order-status", kwargs={"order_number": order.order_number}),
            {"status": "READY"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_staff_queue_filters(self):
        order = self.pickup_order()
        change_order_status(order_id=order.id, new_status="CONFIRMED", system=True)
        self.client.force_authenticate(user=self.staff)

        confirmed = self.client.get(reverse("staff-order-list"), {"status": "confirmed"})
        pending = self.client.get(reverse("staff-order-list"), {"status": "PENDING"})
        by_date = self.client.get(reverse("staff-order-list"), {"date": PICKUP_DATE})

        self.assertEqual(confirmed.data["count"], 1)
        self.assertEqual(pending.data["count"], 0)
        self.assertEqual(by_date.data["count"], 1)

    def test_checkout_endpoint_applies_promotion_code(self):
        Promotion.objects.create(
            name="Fixed",
            code="R100",
            discount_type=Promotion.DiscountType.FIXED,
            discount_value=Decimal("100.00"),
            starts_at=timezone.now() - timedelta(days=1),
            expires_at=timezone.now() + timedelta(days=1),
        )
        self.fill_cart()
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("checkout"),
            {
                "fulfillment_type": "PICKUP",
                "scheduled_date": PICKUP_DATE,
                "scheduled_time": "10:00:00",
                "promotion_code": "R100",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Decimal(response.data["discount_amount"]), Decimal("100.00"))
        self.assertEqual(Decimal(response.data["total"]), Decimal("400.00"))

    def test_checkout_with_bad_code_is_400(self):
        self.fill_cart()
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("checkout"),
            {
                "fulfillment_type": "PICKUP",
                "scheduled_date": PICKUP_DATE,
                "scheduled_time": "10:00:00",
                "promotion_code": "NOPE",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_redeem_endpoint_now_reduces_the_order_total(self):
        Promotion.objects.create(
            name="Fixed",
            code="R50",
            discount_type=Promotion.DiscountType.FIXED,
            discount_value=Decimal("50.00"),
            starts_at=timezone.now() - timedelta(days=1),
            expires_at=timezone.now() + timedelta(days=1),
        )
        order = self.pickup_order()
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("promotion-redeem"),
            {"order_id": order.id, "code": "R50"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        order.refresh_from_db()
        self.assertEqual(order.discount_amount, Decimal("50.00"))
        self.assertEqual(order.total, Decimal("450.00"))


class PickupSlotRuleTests(Fixture, APITestCase):
    def setUp(self):
        self.make_fixture()
        self.client.force_authenticate(user=self.user)

    def post(self, day, at="10:00:00"):
        self.fill_cart()
        return self.client.post(
            reverse("checkout"),
            {"fulfillment_type": "PICKUP", "scheduled_date": day, "scheduled_time": at},
            format="json",
        )

    def test_too_soon_is_rejected(self):
        response = self.post(timezone.localdate().isoformat())
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_closed_day_is_rejected(self):
        day = date.fromisoformat(PICKUP_DATE)
        while day.weekday() != 6:  # Sunday (closed by default)
            day += timedelta(days=1)

        response = self.post(day.isoformat())

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_outside_opening_hours_is_rejected(self):
        response = self.post(PICKUP_DATE, at="22:00:00")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_slot_is_accepted(self):
        response = self.post(PICKUP_DATE)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
