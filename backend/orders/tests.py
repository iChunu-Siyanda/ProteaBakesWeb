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


from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from cart.models import Cart, CartItem
from catalog.models import Category, Product
from fulfillment.models import Booking, Delivery
from users.models import User

from .models import Order, OrderItem


class CheckoutAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="customer@example.com",
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
            description="Chocolate cake",
            price="250.00",
            sku="CAKE-001",
            is_active=True,
        )

        self.client.force_authenticate(user=self.user)

    def create_cart_with_item(self, quantity=2):
        cart = Cart.objects.create(user=self.user)

        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=quantity,
        )

        return cart

    def test_unauthenticated_user_cannot_checkout(self):
        self.client.force_authenticate(user=None)

        response = self.client.post(
            reverse("checkout"),
            {"fulfillment_type": "PICKUP"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_empty_cart_cannot_checkout(self):
        Cart.objects.create(user=self.user)

        response = self.client.post(
            reverse("checkout"),
            {
                "fulfillment_type": "PICKUP",
                "scheduled_date": "2026-09-30",
                "scheduled_time": "10:00:00",
            },
            format="json",
        )

        print(response.data)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn("empty", response.data["detail"].lower())

    def test_pickup_checkout_creates_order(self):
        cart = self.create_cart_with_item(quantity=2)

        response = self.client.post(
            reverse("checkout"),
            {
                "fulfillment_type": "PICKUP",
                "scheduled_date": "2026-09-30",
                "scheduled_time": "10:00:00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        order = Order.objects.get(
            order_number=response.data["order_number"]
        )

        self.assertEqual(order.user, self.user)
        self.assertEqual(
            order.fulfillment_type,
            Order.FulfillmentType.PICKUP,
        )
        self.assertEqual(order.subtotal, Decimal("500.00"))
        self.assertEqual(order.delivery_fee, Decimal("0.00"))
        self.assertEqual(order.total, Decimal("500.00"))

        self.assertTrue(
            Booking.objects.filter(order=order).exists()
        )

        self.assertFalse(
            Delivery.objects.filter(order=order).exists()
        )

        cart.refresh_from_db()

        self.assertEqual(
            cart.status,
            Cart.Status.CONVERTED,
        )

    def test_delivery_checkout_creates_delivery(self):
        self.create_cart_with_item(quantity=2)

        response = self.client.post(
            reverse("checkout"),
            {
                "fulfillment_type": "DELIVERY",
                "delivery_data": {
                    "recipient_name": "Jane Doe",
                    "phone_number": "0123456789",
                    "address_line_1": "123 Main Street",
                    "city": "Welkom",
                    "province": "Free State",
                    "postal_code": "9460",
                },
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        order = Order.objects.get(
            order_number=response.data["order_number"]
        )

        self.assertEqual(
            order.fulfillment_type,
            Order.FulfillmentType.DELIVERY,
        )

        self.assertEqual(
            order.delivery_fee,
            Decimal("50.00"),
        )

        self.assertEqual(
            order.total,
            Decimal("550.00"),
        )

        delivery = Delivery.objects.get(order=order)

        self.assertEqual(
            delivery.recipient_name,
            "Jane Doe",
        )
        self.assertEqual(
            delivery.address_line_1,
            "123 Main Street",
        )

        self.assertFalse(
            Booking.objects.filter(order=order).exists()
        )

    def test_delivery_requires_delivery_data(self):
        self.create_cart_with_item()

        response = self.client.post(
            reverse("checkout"),
            {"fulfillment_type": "DELIVERY"},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_pickup_rejects_delivery_data(self):
        self.create_cart_with_item()

        response = self.client.post(
            reverse("checkout"),
            {
                "fulfillment_type": "PICKUP",
                "delivery_data": {
                    "recipient_name": "Jane Doe",
                    "phone_number": "0123456789",
                    "address_line_1": "123 Main Street",
                    "city": "Welkom",
                    "province": "Free State",
                    "postal_code": "9460",
                },
                "scheduled_time": "10:00:00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_order_items_store_price_snapshot(self):
        self.create_cart_with_item(quantity=2)

        response = self.client.post(
            reverse("checkout"),
            {
                "fulfillment_type": "PICKUP",
                "scheduled_date": "2026-09-30",
                "scheduled_time": "10:00:00",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        order = Order.objects.get(
            order_number=response.data["order_number"]
        )

        order_item = OrderItem.objects.get(order=order)

        self.assertEqual(
            order_item.product_name,
            "Chocolate Cake",
        )
        self.assertEqual(
            order_item.unit_price,
            Decimal("250.00"),
        )
        self.assertEqual(
            order_item.quantity,
            2,
        )
        self.assertEqual(
            order_item.subtotal,
            Decimal("500.00"),
        )

        # Change the product's current price.
        self.product.price = Decimal("300.00")
        self.product.save()

        order_item.refresh_from_db()

        # Historical order price must remain unchanged.
        self.assertEqual(
            order_item.unit_price,
            Decimal("250.00"),
        )
        self.assertEqual(
            order_item.subtotal,
            Decimal("500.00"),
        )

    def test_checkout_does_not_trust_client_total(self):
        self.create_cart_with_item(quantity=2)

        response = self.client.post(
            reverse("checkout"),
            {
                "fulfillment_type": "PICKUP",
                "total": "1.00",
                "subtotal": "1.00",
                "scheduled_date": "2026-09-30",
                "scheduled_time": "10:00:00",
            },
            format="json",
        )

        print(response.status_code)
        print(response.data)

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        order = Order.objects.get(
            order_number=response.data["order_number"]
        )

        self.assertEqual(
            order.subtotal,
            Decimal("500.00"),
        )

        self.assertEqual(
            order.total,
            Decimal("500.00"),
        )

    def test_inactive_product_cannot_be_checked_out(self):
        cart = self.create_cart_with_item(quantity=1)

        self.product.is_active = False
        self.product.save()

        response = self.client.post(
            reverse("checkout"),
            {"fulfillment_type": "PICKUP","scheduled_date": "2026-09-30",},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        cart.refresh_from_db()

        self.assertEqual(
            cart.status,
            Cart.Status.ACTIVE,
        )

        self.assertFalse(
            Order.objects.filter(user=self.user).exists()
        )

    def test_pickup_requires_scheduled_date(self):
        self.create_cart_with_item()

        response = self.client.post(
            reverse("checkout"),
            {
                "fulfillment_type": "PICKUP",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn(
            "scheduled_date",
            response.data,
        )
        