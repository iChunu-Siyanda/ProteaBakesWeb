from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from catalog.models import Category, Product
from orders.models import Order
from payments.models import Payment, PaymentTransaction, WebhookEvent
from users.models import User


class PaymentModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="customer@example.com",
            password="securepassword123",
            first_name="John",
            last_name="Doe",
        )

        self.category = Category.objects.create(
            name="Cakes",
            slug="cakes",
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Chocolate Cake",
            slug="chocolate-cake",
            price="250.00",
            sku="CAKE-001",
        )

        self.order = Order.objects.create(
            user=self.user,
            order_number="PB-000001",
            fulfillment_type=Order.FulfillmentType.PICKUP,
            subtotal=Decimal("250.00"),
            discount_amount=Decimal("0.00"),
            delivery_fee=Decimal("0.00"),
            total=Decimal("250.00"),
        )

    def test_payment_amount_must_be_positive(self):
        payment = Payment(
            order=self.order,
            amount=Decimal("0.00"),
            currency="ZAR",
            status=Payment.Status.PENDING,
        )

        with self.assertRaises(ValidationError):
            payment.full_clean()

    def test_payment_transaction_amount_must_be_positive(self):
        payment = Payment.objects.create(
            order=self.order,
            amount=Decimal("250.00"),
            currency="ZAR",
            status=Payment.Status.PENDING,
        )

        transaction = PaymentTransaction(
            payment=payment,
            transaction_reference="TXN-001",
            transaction_type=PaymentTransaction.TransactionType.PAYMENT,
            amount=Decimal("0.00"),
            status=PaymentTransaction.Status.PENDING,
        )

        with self.assertRaises(ValidationError):
            transaction.full_clean()


from payments.models import Payment
from payments.services import PaymentProvider, initiate_payment


class PaymentServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="customer@example.com",
            password="securepassword123",
            first_name="John",
            last_name="Doe",
        )

        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="securepassword123",
            first_name="Jane",
            last_name="Doe",
        )

        self.category = Category.objects.create(
            name="Cakes",
            slug="cakes",
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Chocolate Cake",
            slug="chocolate-cake",
            price=Decimal("250.00"),
            sku="CAKE-001",
        )

        self.order = Order.objects.create(
            user=self.user,
            order_number="PB-000001",
            fulfillment_type=Order.FulfillmentType.PICKUP,
            subtotal=Decimal("500.00"),
            discount_amount=Decimal("0.00"),
            delivery_fee=Decimal("0.00"),
            total=Decimal("500.00"),
        )

        self.provider = PaymentProvider()

    def test_initiate_payment_creates_payment(self):
        payment, provider_result = initiate_payment(
            user=self.user,
            order_id=self.order.id,
            provider=self.provider,
        )

        self.assertIsNotNone(payment)
        self.assertEqual(payment.order, self.order)
        self.assertEqual(payment.provider, "test")
        self.assertEqual(payment.amount, Decimal("500.00"))
        self.assertEqual(payment.currency, "ZAR")
        self.assertEqual(payment.status, Payment.Status.PENDING)

        self.assertEqual(
            payment.provider_reference,
            "TEST-PB-000001",
        )

        self.assertIn("checkout_url", provider_result)

    def test_payment_amount_comes_from_order_total(self):
        self.order.total = Decimal("999.00")
        self.order.save(update_fields=["total"])

        payment, _ = initiate_payment(
            user=self.user,
            order_id=self.order.id,
            provider=self.provider,
        )

        self.assertEqual(
            payment.amount,
            Decimal("999.00"),
        )

    def test_user_cannot_pay_another_users_order(self):
        with self.assertRaisesMessage(
            ValueError,
            "Order not found.",
        ):
            initiate_payment(
                user=self.other_user,
                order_id=self.order.id,
                provider=self.provider,
            )

        self.assertFalse(
            Payment.objects.filter(order=self.order).exists()
        )

    def test_cancelled_order_cannot_be_paid(self):
        self.order.status = Order.Status.CANCELLED
        self.order.save(update_fields=["status"])

        with self.assertRaisesMessage(
            ValueError,
            "Cancelled orders cannot be paid.",
        ):
            initiate_payment(
                user=self.user,
                order_id=self.order.id,
                provider=self.provider,
            )

        self.assertFalse(
            Payment.objects.filter(order=self.order).exists()
        )

    def test_order_cannot_have_multiple_payments(self):
        Payment.objects.create(
            order=self.order,
            provider="test",
            provider_reference="TEST-EXISTING",
            amount=Decimal("500.00"),
            currency="ZAR",
            status=Payment.Status.PENDING,
        )

        with self.assertRaisesMessage(
            ValueError,
            "This order already has a payment.",
        ):
            initiate_payment(
                user=self.user,
                order_id=self.order.id,
                provider=self.provider,
            )

        self.assertEqual(
            Payment.objects.filter(order=self.order).count(),
            1,
        )

    def test_nonexistent_order_cannot_be_paid(self):
        with self.assertRaisesMessage(
            ValueError,
            "Order not found.",
        ):
            initiate_payment(
                user=self.user,
                order_id=999999,
                provider=self.provider,
            )

        self.assertEqual(
            Payment.objects.count(),
            0,
        )

    def test_provider_failure_rolls_back_payment_creation(self):
        class FailingPaymentProvider:
            name = "failing_test"

            def create_payment(self, *, order):
                raise RuntimeError("Payment provider failed.")

        provider = FailingPaymentProvider()

        with self.assertRaisesMessage(RuntimeError, "Payment provider failed."):
            initiate_payment(
                user=self.user,
                order_id=self.order.id,
                provider=provider,
            )

        self.assertFalse(
            Payment.objects.filter(order=self.order).exists()
        )


from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse


class PaymentAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="customer@example.com",
            password="securepassword123",
            first_name="John",
            last_name="Doe",
        )

        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="securepassword123",
            first_name="Jane",
            last_name="Doe",
        )

        self.category = Category.objects.create(
            name="Cakes",
            slug="cakes",
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Chocolate Cake",
            slug="chocolate-cake",
            price="250.00",
            sku="CAKE-001",
        )

        self.order = Order.objects.create(
            user=self.user,
            order_number="PB-000001",
            fulfillment_type=Order.FulfillmentType.PICKUP,
            subtotal="500.00",
            discount_amount="0.00",
            delivery_fee="0.00",
            total="500.00",
        )

        self.url = reverse("payment-initiate")

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_unauthenticated_user_cannot_initiate_payment(self):
        response = self.client.post(
            self.url,
            {"order_id": self.order.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_can_initiate_payment(self):
        self.authenticate(self.user)

        response = self.client.post(
            self.url,
            {"order_id": self.order.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["order_id"], self.order.id)
        self.assertEqual(response.data["provider"], "test")
        self.assertEqual(response.data["amount"], Decimal("500.00"))
        self.assertEqual(response.data["currency"], "ZAR")
        self.assertEqual(response.data["status"], Payment.Status.PENDING)
        self.assertIn("checkout_url", response.data)

        self.assertTrue(
            Payment.objects.filter(order=self.order).exists()
        )

    def test_user_cannot_initiate_payment_for_another_users_order(self):
        self.authenticate(self.other_user)

        response = self.client.post(
            self.url,
            {"order_id": self.order.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Order not found.")

        self.assertFalse(
            Payment.objects.filter(order=self.order).exists()
        )

    def test_cancelled_order_cannot_be_paid(self):
        self.order.status = Order.Status.CANCELLED
        self.order.save(update_fields=["status"])

        self.authenticate(self.user)

        response = self.client.post(
            self.url,
            {"order_id": self.order.id},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            response.data["detail"],
            "Cancelled orders cannot be paid.",
        )

    def test_order_cannot_be_paid_twice(self):
        self.authenticate(self.user)

        first_response = self.client.post(
            self.url,
            {"order_id": self.order.id},
            format="json",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )

        second_response = self.client.post(
            self.url,
            {"order_id": self.order.id},
            format="json",
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            second_response.data["detail"],
            "This order already has a payment.",
        )

        self.assertEqual(
            Payment.objects.filter(order=self.order).count(),
            1,
        )

    def test_nonexistent_order_returns_400(self):
        self.authenticate(self.user)

        response = self.client.post(
            self.url,
            {"order_id": 999999},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["detail"], "Order not found.")

    def test_order_id_is_required(self):
        self.authenticate(self.user)

        response = self.client.post(
            self.url,
            {},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("order_id", response.data)

    def test_invalid_order_id_is_rejected(self):
        self.authenticate(self.user)

        response = self.client.post(
            self.url,
            {"order_id": "invalid"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("order_id", response.data)


class PaymentWebhookAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="customer@example.com",
            password="securepassword123",
            first_name="John",
            last_name="Doe",
        )

        self.category = Category.objects.create(
            name="Cakes",
            slug="cakes",
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Chocolate Cake",
            slug="chocolate-cake",
            price="250.00",
            sku="CAKE-001",
        )

        self.order = Order.objects.create(
            user=self.user,
            order_number="PB-000001",
            fulfillment_type=Order.FulfillmentType.PICKUP,
            subtotal="500.00",
            discount_amount="0.00",
            delivery_fee="0.00",
            total="500.00",
        )

        self.payment = Payment.objects.create(
            order=self.order,
            provider="test",
            provider_reference="TEST-PB-000001",
            amount="500.00",
            currency="ZAR",
            status=Payment.Status.PENDING,
        )

        self.url = reverse("payment-webhook")

    def webhook(self, event_id, status_value):
        return self.client.post(
            self.url,
            {
                "provider_reference": self.payment.provider_reference,
                "status": status_value,
            },
            format="json",
            HTTP_X_WEBHOOK_EVENT_ID=event_id,
            HTTP_X_WEBHOOK_EVENT_TYPE="payment.updated",
        )

    def test_successful_payment_webhook(self):
        response = self.webhook(
            event_id="evt-success-001",
            status_value="succeeded",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data["processed"])
        self.assertEqual(response.data["payment_id"], self.payment.id)

        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.SUCCEEDED,
        )
        self.assertIsNotNone(self.payment.paid_at)
        self.assertEqual(
            self.order.status,
            Order.Status.CONFIRMED,
        )

        self.assertTrue(
            WebhookEvent.objects.filter(
                event_id="evt-success-001",
                processed=True,
            ).exists()
        )

    def test_failed_payment_webhook(self):
        response = self.webhook(
            event_id="evt-failed-001",
            status_value="failed",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.payment.refresh_from_db()
        self.order.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.FAILED,
        )

        self.assertEqual(
            self.order.status,
            Order.Status.PENDING,
        )

        self.assertTrue(
            WebhookEvent.objects.filter(
                event_id="evt-failed-001",
                processed=True,
            ).exists()
        )

    def test_duplicate_webhook_is_idempotent(self):
        event_id = "evt-duplicate-001"

        first_response = self.webhook(
            event_id=event_id,
            status_value="succeeded",
        )

        second_response = self.webhook(
            event_id=event_id,
            status_value="succeeded",
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_200_OK,
        )

        self.assertTrue(second_response.data["processed"])

        self.assertEqual(
            WebhookEvent.objects.filter(
                event_id=event_id,
            ).count(),
            1,
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.SUCCEEDED,
        )

    def test_webhook_requires_event_id(self):
        response = self.client.post(
            self.url,
            {
                "provider_reference": self.payment.provider_reference,
                "status": "succeeded",
            },
            format="json",
            HTTP_X_WEBHOOK_EVENT_TYPE="payment.updated",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "Webhook event ID is required.",
        )

    def test_webhook_requires_event_type(self):
        response = self.client.post(
            self.url,
            {
                "provider_reference": self.payment.provider_reference,
                "status": "succeeded",
            },
            format="json",
            HTTP_X_WEBHOOK_EVENT_ID="evt-no-type-001",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "Webhook event type is required.",
        )

    def test_webhook_requires_provider_reference(self):
        response = self.client.post(
            self.url,
            {
                "status": "succeeded",
            },
            format="json",
            HTTP_X_WEBHOOK_EVENT_ID="evt-no-reference-001",
            HTTP_X_WEBHOOK_EVENT_TYPE="payment.updated",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "Provider reference is required.",
        )

    def test_webhook_returns_400_for_unknown_payment(self):
        response = self.client.post(
            self.url,
            {
                "provider_reference": "UNKNOWN-PAYMENT",
                "status": "succeeded",
            },
            format="json",
            HTTP_X_WEBHOOK_EVENT_ID="evt-unknown-payment-001",
            HTTP_X_WEBHOOK_EVENT_TYPE="payment.updated",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "Payment not found.",
        )

    def test_webhook_rejects_unsupported_payment_status(self):
        response = self.webhook(
            event_id="evt-invalid-status-001",
            status_value="processing",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "Unsupported payment status.",
        )

        self.payment.refresh_from_db()

        self.assertEqual(
            self.payment.status,
            Payment.Status.PENDING,
        )

    def test_webhook_is_public(self):
        response = self.webhook(
            event_id="evt-public-001",
            status_value="succeeded",
        )

        self.assertNotEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

