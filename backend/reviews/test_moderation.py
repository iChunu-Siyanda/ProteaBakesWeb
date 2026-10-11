from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditLog
from catalog.models import Category, Product
from orders.models import Order, OrderItem
from reviews.models import Review
from users.models import User


class ReviewModerationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="c@example.com", password="x-long-passphrase-1",
            first_name="Jane", last_name="Doe",
        )
        self.staff = User.objects.create_user(
            email="s@example.com", password="x-long-passphrase-1", is_staff=True
        )
        category = Category.objects.create(name="Cakes", slug="cakes")
        self.product = Product.objects.create(
            category=category, name="Cake", slug="cake", price="100.00", sku="C1"
        )
        order = Order.objects.create(
            user=self.user, order_number="PB-R1", fulfillment_type="PICKUP",
            subtotal="100.00", discount_amount="0.00", delivery_fee="0.00",
            total="100.00", status=Order.Status.COMPLETED,
        )
        item = OrderItem.objects.create(
            order=order, product=self.product, product_name="Cake",
            unit_price="100.00", quantity=1, subtotal="100.00",
        )
        self.review = Review.objects.create(
            user=self.user, product=self.product, order_item=item, rating=5, comment="Lovely"
        )
        self.list_url = reverse("product-review-list", kwargs={"product_id": self.product.id})

    def test_pending_reviews_are_not_public(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 0)

    def test_published_reviews_are_public_without_email(self):
        self.review.status = Review.Status.PUBLISHED
        self.review.save()

        response = self.client.get(self.list_url)

        self.assertEqual(response.data["count"], 1)
        row = response.data["results"][0]
        self.assertEqual(row["reviewer"], "Jane D.")
        self.assertNotIn("c@example.com", str(row))

    def test_customer_cannot_moderate(self):
        self.client.force_authenticate(user=self.user)

        response = self.client.post(
            reverse("review-moderate", kwargs={"review_id": self.review.id}),
            {"status": "PUBLISHED"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_can_publish_and_it_is_audited(self):
        self.client.force_authenticate(user=self.staff)

        queue = self.client.get(reverse("staff-review-list"))
        self.assertEqual(queue.data["count"], 1)

        response = self.client.post(
            reverse("review-moderate", kwargs={"review_id": self.review.id}),
            {"status": "PUBLISHED"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.review.refresh_from_db()
        self.assertEqual(self.review.status, Review.Status.PUBLISHED)
        self.assertTrue(AuditLog.objects.filter(action="REVIEW_MODERATED").exists())

    def test_cannot_moderate_back_to_pending_or_unknown_review(self):
        self.client.force_authenticate(user=self.staff)

        bad = self.client.post(
            reverse("review-moderate", kwargs={"review_id": self.review.id}),
            {"status": "PENDING"},
            format="json",
        )
        missing = self.client.post(
            reverse("review-moderate", kwargs={"review_id": 9999}),
            {"status": "PUBLISHED"},
            format="json",
        )

        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(missing.status_code, status.HTTP_404_NOT_FOUND)
