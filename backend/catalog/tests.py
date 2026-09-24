from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from catalog.models import Category, Product


class ProductModelTests(TestCase):

    def setUp(self):
        self.category = Category.objects.create(
            name="Cakes",
            slug="cakes",
        )

    def test_product_can_be_created(self):
        product = Product.objects.create(
            category=self.category,
            name="Chocolate Cake",
            slug="chocolate-cake",
            description="A chocolate cake.",
            price="250.00",
            sku="CAKE-001",
        )

        product.refresh_from_db()

        self.assertEqual(product.name, "Chocolate Cake")
        self.assertEqual(product.price, Decimal("250.00"))

    def test_negative_price_is_invalid(self):
        product = Product(
            category=self.category,
            name="Invalid Cake",
            slug="invalid-cake",
            price="-10.00",
            sku="CAKE-002",
        )

        with self.assertRaises(ValidationError):
            product.full_clean()
