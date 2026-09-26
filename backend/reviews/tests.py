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


from decimal import Decimal

from django.contrib.auth import get_user_model

from reviews.services import create_review

User = get_user_model()

class ReviewServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="password123",
        )

        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="password123",
        )

        self.category = Category.objects.create(
            name="Cakes",
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Chocolate Cake",
            description="Chocolate cake",
            price=Decimal("250.00"),
            is_active=True,
        )

        self.order = Order.objects.create(
            user=self.user,
            status=Order.Status.COMPLETED,
            fulfillment_type=Order.FulfillmentType.PICKUP,
            subtotal=Decimal("250.00"),
            discount_amount=Decimal("0.00"),
            delivery_fee=Decimal("0.00"),
            total=Decimal("250.00"),
        )

        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            unit_price=self.product.price,
            quantity=1,
            subtotal=Decimal("250.00"),
        )

    def test_create_review_success(self):
        review = create_review(
            user=self.user,
            order_item_id=self.order_item.id,
            product_id=self.product.id,
            rating=5,
            comment="Excellent cake!",
        )

        self.assertIsNotNone(review.pk)
        self.assertEqual(review.user, self.user)
        self.assertEqual(review.product, self.product)
        self.assertEqual(review.order_item, self.order_item)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.comment, "Excellent cake!")
        self.assertEqual(
            review.status,
            Review.Status.PENDING,
        )

    def test_review_product_comes_from_order_item(self):
        review = create_review(
            user=self.user,
            order_item_id=self.order_item.id,
            product_id=self.product.id,
            rating=4,
        )

        self.assertEqual(review.product_id, self.order_item.product_id)

    def test_nonexistent_order_item_rejected(self):
        with self.assertRaisesMessage(
            ValueError,
            "Order item not found.",
        ):
            create_review(
                user=self.user,
                order_item_id=999999,
                product_id=self.product.id,
                rating=5,
            )

    def test_other_user_cannot_review_order_item(self):
        with self.assertRaisesMessage(
            ValueError,
            "You cannot review this order item.",
        ):
            create_review(
                user=self.other_user,
                order_item_id=self.order_item.id,
                product_id=self.product.id,
                rating=5,
            )

    def test_pending_order_cannot_be_reviewed(self):
        self.order.status = Order.Status.PENDING
        self.order.save()

        with self.assertRaisesMessage(
            ValueError,
            "Only completed orders can be reviewed.",
        ):
            create_review(
                user=self.user,
                order_item_id=self.order_item.id,
                product_id=self.product.id,
                rating=5,
            )

    def test_confirmed_order_cannot_be_reviewed(self):
        self.order.status = Order.Status.CONFIRMED
        self.order.save()

        with self.assertRaisesMessage(
            ValueError,
            "Only completed orders can be reviewed.",
        ):
            create_review(
                user=self.user,
                order_item_id=self.order_item.id,
                product_id=self.product.id,
                rating=5,
            )

    def test_cancelled_order_cannot_be_reviewed(self):
        self.order.status = Order.Status.CANCELLED
        self.order.save()

        with self.assertRaisesMessage(
            ValueError,
            "Only completed orders can be reviewed.",
        ):
            create_review(
                user=self.user,
                order_item_id=self.order_item.id,
                product_id=self.product.id,
                rating=5,
            )

    def test_product_must_match_order_item(self):
        another_product = Product.objects.create(
            category=self.category,
            name="Vanilla Cake",
            slug="vanilla-cake",
            sku="VANILLA-001",
            description="Vanilla cake",
            price=Decimal("200.00"),
            is_active=True,
        )

        with self.assertRaisesMessage(
            ValueError,
            "Product does not match the order item.",
        ):
            create_review(
                user=self.user,
                order_item_id=self.order_item.id,
                product_id=another_product.id,
                rating=5,
            )

    def test_order_item_can_only_be_reviewed_once(self):
        create_review(
            user=self.user,
            order_item_id=self.order_item.id,
            product_id=self.product.id,
            rating=5,
        )

        with self.assertRaisesMessage(
            ValueError,
            "This order item has already been reviewed.",
        ):
            create_review(
                user=self.user,
                order_item_id=self.order_item.id,
                product_id=self.product.id,
                rating=4,
            )

    def test_rating_below_one_rejected(self):
        with self.assertRaisesMessage(
            ValueError,
            "Rating must be between 1 and 5.",
        ):
            create_review(
                user=self.user,
                order_item_id=self.order_item.id,
                product_id=self.product.id,
                rating=0,
            )

    def test_rating_above_five_rejected(self):
        with self.assertRaisesMessage(
            ValueError,
            "Rating must be between 1 and 5.",
        ):
            create_review(
                user=self.user,
                order_item_id=self.order_item.id,
                product_id=self.product.id,
                rating=6,
            )

    def test_comment_is_optional(self):
        review = create_review(
            user=self.user,
            order_item_id=self.order_item.id,
            product_id=self.product.id,
            rating=4,
        )

        self.assertEqual(review.comment, "")

    def test_review_starts_as_pending(self):
        review = create_review(
            user=self.user,
            order_item_id=self.order_item.id,
            product_id=self.product.id,
            rating=5,
        )

        self.assertEqual(
            review.status,
            Review.Status.PENDING,
        )

    def test_different_order_items_can_be_reviewed(self):
        second_product = Product.objects.create(
            category=self.category,
            name="Red Velvet Cake",
            slug="red-velvet-cake",
            sku="REDVELVET-001",
            description="Red velvet cake",
            price=Decimal("300.00"),
            is_active=True,
        )

        second_item = OrderItem.objects.create(
            order=self.order,
            product=second_product,
            product_name=second_product.name,
            unit_price=second_product.price,
            quantity=1,
            subtotal=Decimal("300.00"),
        )

        first_review = create_review(
            user=self.user,
            order_item_id=self.order_item.id,
            product_id=self.product.id,
            rating=5,
        )

        second_review = create_review(
            user=self.user,
            order_item_id=second_item.id,
            product_id=second_product.id,
            rating=4,
        )

        self.assertNotEqual(first_review.pk, second_review.pk)
        self.assertEqual(
            Review.objects.filter(user=self.user).count(),
            2,
        )


from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()

class ReviewAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="password123",
        )

        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="password123",
        )

        self.category = Category.objects.create(
            name="Cakes",
            slug="cakes",
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Chocolate Cake",
            slug="chocolate-cake",
            sku="CHOCOLATE-001",
            description="Chocolate cake",
            price=Decimal("250.00"),
            is_active=True,
        )

        self.order = Order.objects.create(
            user=self.user,
            status=Order.Status.COMPLETED,
            fulfillment_type=Order.FulfillmentType.PICKUP,
            subtotal=Decimal("250.00"),
            discount_amount=Decimal("0.00"),
            delivery_fee=Decimal("0.00"),
            total=Decimal("250.00"),
        )

        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            product_name=self.product.name,
            unit_price=self.product.price,
            quantity=1,
            subtotal=Decimal("250.00"),
        )

        self.url = reverse("review-create")

    def _create_product(
        self,
        *,
        name,
        slug,
        sku,
        price=Decimal("200.00"),
    ):
        return Product.objects.create(
            category=self.category,
            name=name,
            slug=slug,
            sku=sku,
            description=name,
            price=price,
            is_active=True,
        )

    def _create_order(
        self,
        *,
        user,
        status=Order.Status.COMPLETED,
        order_number=None,
    ):
        if order_number is None:
            order_number = f"TEST-{Order.objects.count() + 1:03d}"

        return Order.objects.create(
            user=user,
            order_number=order_number,
            status=status,
            fulfillment_type=Order.FulfillmentType.PICKUP,
            subtotal=Decimal("250.00"),
            discount_amount=Decimal("0.00"),
            delivery_fee=Decimal("0.00"),
            total=Decimal("250.00"),
        )

    def _create_order_item(
        self,
        *,
        order,
        product,
        quantity=1,
    ):
        return OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            unit_price=product.price,
            quantity=quantity,
            subtotal=product.price * quantity,
        )

    # ---------------------------------------------------------
    # Authentication
    # ---------------------------------------------------------

    def test_create_review_requires_authentication(self):
        response = self.client.post(
            self.url,
            {
                "order_item_id": self.order_item.id,
                "product_id": self.product.id,
                "rating": 5,
                "comment": "Excellent!",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    # ---------------------------------------------------------
    # Successful creation
    # ---------------------------------------------------------

    def test_create_review_success(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            {
                "order_item_id": self.order_item.id,
                "product_id": self.product.id,
                "rating": 5,
                "comment": "Excellent cake!",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["product_id"],
            self.product.id,
        )
        self.assertEqual(
            response.data["order_item_id"],
            self.order_item.id,
        )
        self.assertEqual(
            response.data["rating"],
            5,
        )
        self.assertEqual(
            response.data["comment"],
            "Excellent cake!",
        )
        self.assertEqual(
            response.data["status"],
            Review.Status.PENDING,
        )
        self.assertIn("id", response.data)
        self.assertIn("created_at", response.data)

        self.assertTrue(
            Review.objects.filter(
                user=self.user,
                product=self.product,
                order_item=self.order_item,
            ).exists()
        )

    def test_create_review_without_comment(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            {
                "order_item_id": self.order_item.id,
                "product_id": self.product.id,
                "rating": 4,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["comment"],
            "",
        )

    # ---------------------------------------------------------
    # Ownership
    # ---------------------------------------------------------

    def test_other_user_cannot_review_order_item(self):
        self.client.force_authenticate(user=self.other_user)

        response = self.client.post(
            self.url,
            {
                "order_item_id": self.order_item.id,
                "product_id": self.product.id,
                "rating": 5,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "You cannot review this order item.",
        )

        self.assertFalse(
            Review.objects.filter(
                order_item=self.order_item,
            ).exists()
        )

    # ---------------------------------------------------------
    # Order status
    # ---------------------------------------------------------

    def test_pending_order_cannot_be_reviewed(self):
        self.order.status = Order.Status.PENDING
        self.order.save()

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            {
                "order_item_id": self.order_item.id,
                "product_id": self.product.id,
                "rating": 5,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "Only completed orders can be reviewed.",
        )

    def test_confirmed_order_cannot_be_reviewed(self):
        self.order.status = Order.Status.CONFIRMED
        self.order.save()

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            {
                "order_item_id": self.order_item.id,
                "product_id": self.product.id,
                "rating": 5,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "Only completed orders can be reviewed.",
        )

    def test_cancelled_order_cannot_be_reviewed(self):
        self.order.status = Order.Status.CANCELLED
        self.order.save()

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            {
                "order_item_id": self.order_item.id,
                "product_id": self.product.id,
                "rating": 5,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "Only completed orders can be reviewed.",
        )

    # ---------------------------------------------------------
    # Product validation
    # ---------------------------------------------------------

    def test_product_must_match_order_item(self):
        another_product = self._create_product(
            name="Vanilla Cake",
            slug="vanilla-cake",
            sku="VANILLA-001",
        )

        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            {
                "order_item_id": self.order_item.id,
                "product_id": another_product.id,
                "rating": 5,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "Product does not match the order item.",
        )

    # ---------------------------------------------------------
    # Duplicate reviews
    # ---------------------------------------------------------

    def test_order_item_can_only_be_reviewed_once(self):
        self.client.force_authenticate(user=self.user)

        first_response = self.client.post(
            self.url,
            {
                "order_item_id": self.order_item.id,
                "product_id": self.product.id,
                "rating": 5,
            },
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )

        second_response = self.client.post(
            self.url,
            {
                "order_item_id": self.order_item.id,
                "product_id": self.product.id,
                "rating": 4,
            },
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            second_response.data["detail"],
            "This order item has already been reviewed.",
        )

        self.assertEqual(
            Review.objects.filter(
                order_item=self.order_item,
            ).count(),
            1,
        )

    # ---------------------------------------------------------
    # Rating validation
    # ---------------------------------------------------------

    def test_rating_below_one_rejected(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            {
                "order_item_id": self.order_item.id,
                "product_id": self.product.id,
                "rating": 0,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("rating", response.data)

    def test_rating_above_five_rejected(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            {
                "order_item_id": self.order_item.id,
                "product_id": self.product.id,
                "rating": 6,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("rating", response.data)

    def test_rating_is_required(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            {
                "order_item_id": self.order_item.id,
                "product_id": self.product.id,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("rating", response.data)

    # ---------------------------------------------------------
    # Required IDs
    # ---------------------------------------------------------

    def test_order_item_id_is_required(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            {
                "product_id": self.product.id,
                "rating": 5,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("order_item_id", response.data)

    def test_product_id_is_required(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            {
                "order_item_id": self.order_item.id,
                "rating": 5,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertIn("product_id", response.data)

    def test_nonexistent_order_item_rejected(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            {
                "order_item_id": 999999,
                "product_id": self.product.id,
                "rating": 5,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "Order item not found.",
        )

    # ---------------------------------------------------------
    # Different order items
    # ---------------------------------------------------------

    def test_different_order_items_can_be_reviewed(self):
        second_product = self._create_product(
            name="Red Velvet Cake",
            slug="red-velvet-cake",
            sku="REDVELVET-001",
            price=Decimal("300.00"),
        )

        second_order_item = self._create_order_item(
            order=self.order,
            product=second_product,
        )

        self.client.force_authenticate(user=self.user)

        first_response = self.client.post(
            self.url,
            {
                "order_item_id": self.order_item.id,
                "product_id": self.product.id,
                "rating": 5,
            },
        )

        second_response = self.client.post(
            self.url,
            {
                "order_item_id": second_order_item.id,
                "product_id": second_product.id,
                "rating": 4,
            },
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            Review.objects.filter(
                user=self.user,
            ).count(),
            2,
        )

    # ---------------------------------------------------------
    # Status cannot be controlled by client
    # ---------------------------------------------------------

    def test_client_cannot_set_review_status(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            {
                "order_item_id": self.order_item.id,
                "product_id": self.product.id,
                "rating": 5,
                "status": Review.Status.PUBLISHED,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        review = Review.objects.get(
            order_item=self.order_item,
        )

        self.assertEqual(
            review.status,
            Review.Status.PENDING,
        )

    # ---------------------------------------------------------
    # Comment validation
    # ---------------------------------------------------------

    def test_comment_can_be_blank(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            self.url,
            {
                "order_item_id": self.order_item.id,
                "product_id": self.product.id,
                "rating": 5,
                "comment": "",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

    def test_comment_can_contain_text(self):
        self.client.force_authenticate(user=self.user)

        comment = "The cake was fresh and delicious."

        response = self.client.post(
            self.url,
            {
                "order_item_id": self.order_item.id,
                "product_id": self.product.id,
                "rating": 5,
                "comment": comment,
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            response.data["comment"],
            comment,
        )
