from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from catalog.models import Category, Product
from orders.models import Order
from payments.models import Payment, PaymentTransaction
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
            