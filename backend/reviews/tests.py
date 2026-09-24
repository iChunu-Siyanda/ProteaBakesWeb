from django.core.exceptions import ValidationError
from django.test import TestCase

from catalog.models import Category, Product
from orders.models import Order, OrderItem
from reviews.models import Review
from users.models import User


class ReviewModelTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="customer@example.com",
            password="securepassword123",
            first_name="John",
            last_name="Doe",
        )

        category = Category.objects.create(
            name="Cakes",
            slug="cakes",
        )

        self.product = Product.objects.create(
            category=category,
            name="Chocolate Cake",
            slug="chocolate-cake",
            price="250.00",
            sku="CAKE-001",
        )

        self.order = Order.objects.create(
            user=self.user,
            order_number="PB-000001",
            fulfillment_type=Order.FulfillmentType.PICKUP,
            status=Order.Status.COMPLETED,
            subtotal="250.00",
            discount_amount="0.00",
            delivery_fee="0.00",
            total="250.00",
        )

        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name="Chocolate Cake",
            unit_price="250.00",
            quantity=1,
            subtotal="250.00",
        )

    def test_rating_must_be_between_one_and_five(self):
        review = Review(
            user=self.user,
            product=self.product,
            order_item=self.order_item,
            rating=6,
        )

        with self.assertRaises(ValidationError):
            review.full_clean()

    def test_review_can_be_created(self):
        review = Review.objects.create(
            user=self.user,
            product=self.product,
            order_item=self.order_item,
            rating=5,
            comment="Excellent cake!",
        )

        self.assertEqual(review.rating, 5)
        self.assertEqual(review.status, Review.Status.PENDING)

    def test_order_item_can_only_have_one_review(self):
        Review.objects.create(
            user=self.user,
            product=self.product,
            order_item=self.order_item,
            rating=5,
        )

        with self.assertRaises(Exception):
            Review.objects.create(
                user=self.user,
                product=self.product,
                order_item=self.order_item,
                rating=4,
            )
            