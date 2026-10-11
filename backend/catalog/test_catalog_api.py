from decimal import Decimal

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import Category, Product
from inventory.models import InventoryItem
from orders.models import Order, OrderItem
from reviews.models import Review
from users.models import User


class CatalogAPITests(APITestCase):
    def setUp(self):
        self.cakes = Category.objects.create(name="Cakes", slug="cakes")
        self.bread = Category.objects.create(name="Bread", slug="bread")
        self.cake = Product.objects.create(
            category=self.cakes, name="Chocolate Cake", slug="chocolate-cake",
            description="Rich and dark", price=Decimal("250.00"), sku="C1",
        )
        self.loaf = Product.objects.create(
            category=self.bread, name="Rye Loaf", slug="rye-loaf",
            price=Decimal("45.00"), sku="B1",
        )

    def names(self, **params):
        response = self.client.get(reverse("product-list"), params)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        return [p["name"] for p in response.data]

    def test_categories_are_public(self):
        response = self.client.get(reverse("category-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual({c["slug"] for c in response.data}, {"cakes", "bread"})

    def test_filter_by_category(self):
        self.assertEqual(self.names(category="bread"), ["Rye Loaf"])

    def test_search(self):
        self.assertEqual(self.names(search="dark"), ["Chocolate Cake"])

    def test_ordering(self):
        self.assertEqual(self.names(ordering="price"), ["Rye Loaf", "Chocolate Cake"])
        self.assertEqual(self.names(ordering="-price"), ["Chocolate Cake", "Rye Loaf"])

    def test_lookup_by_slug(self):
        response = self.client.get(reverse("product-by-slug", kwargs={"slug": "rye-loaf"}))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["name"], "Rye Loaf")

    def test_inactive_slug_is_404(self):
        self.loaf.is_active = False
        self.loaf.save()

        response = self.client.get(reverse("product-by-slug", kwargs={"slug": "rye-loaf"}))

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_availability_reflects_stock(self):
        stock = InventoryItem.objects.create(product=self.cake, quantity=0)

        out = self.client.get(reverse("product-detail", kwargs={"pk": self.cake.pk}))
        self.assertFalse(out.data["is_available"])

        stock.quantity = 3
        stock.save()
        back = self.client.get(reverse("product-detail", kwargs={"pk": self.cake.pk}))
        self.assertTrue(back.data["is_available"])

        # Untracked products are always available.
        loaf = self.client.get(reverse("product-detail", kwargs={"pk": self.loaf.pk}))
        self.assertTrue(loaf.data["is_available"])

    def test_rating_counts_only_published_reviews(self):
        user = User.objects.create_user(email="r@example.com", password="x-long-passphrase-1")
        order = Order.objects.create(
            user=user, order_number="PB-REV1", fulfillment_type="PICKUP",
            subtotal="500.00", discount_amount="0.00", delivery_fee="0.00", total="500.00",
            status=Order.Status.COMPLETED,
        )
        for i, (rating, state) in enumerate(
            [(5, "PUBLISHED"), (3, "PUBLISHED"), (1, "PENDING")]
        ):
            item = OrderItem.objects.create(
                order=order, product=self.cake, product_name="Chocolate Cake",
                unit_price="250.00", quantity=1, subtotal="250.00",
            )
            Review.objects.create(
                user=user, product=self.cake, order_item=item, rating=rating, status=state
            )

        response = self.client.get(reverse("product-detail", kwargs={"pk": self.cake.pk}))

        self.assertEqual(response.data["review_count"], 2)
        self.assertEqual(response.data["average_rating"], 4.0)
        empty = self.client.get(reverse("product-detail", kwargs={"pk": self.loaf.pk}))
        self.assertIsNone(empty.data["average_rating"])
