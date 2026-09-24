from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from catalog.models import Category, Product
from orders.models import Order, OrderItem
from users.models import User


class OrderModelTests(TestCase):

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

    def test_order_item_quantity_must_be_at_least_one(self):
        item = OrderItem(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            unit_price=Decimal("250.00"),
            quantity=0,
            subtotal=Decimal("0.00"),
        )

        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_order_item_preserves_product_snapshot(self):
        item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name="Chocolate Cake",
            unit_price=Decimal("250.00"),
            quantity=1,
            subtotal=Decimal("250.00"),
        )

        self.product.name = "Updated Chocolate Cake"
        self.product.price = Decimal("300.00")
        self.product.save()

        item.refresh_from_db()

        self.assertEqual(item.product_name, "Chocolate Cake")
        self.assertEqual(item.unit_price, Decimal("250.00"))
        