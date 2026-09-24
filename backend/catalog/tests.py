from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from catalog.serializers import ProductSerializer
from catalog.models import Category, Product, ProductImage

from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse


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


class ProductSerializerTests(TestCase):

    def setUp(self):
        self.category = Category.objects.create(
            name="Cakes",
            slug="cakes",
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Chocolate Cake",
            slug="chocolate-cake",
            description="Rich chocolate cake.",
            price=Decimal("250.00"),
            sku="CAKE-001",
            is_active=True,
            is_made_to_order=False,
        )

    def test_product_serializer_returns_expected_fields(self):
        serializer = ProductSerializer(self.product)

        self.assertEqual(
            set(serializer.data.keys()),
            {
                "id",
                "name",
                "slug",
                "description",
                "price",
                "sku",
                "category",
                "images",
                "is_active",
                "is_made_to_order",
            },
        )

    def test_product_serializer_includes_category(self):
        serializer = ProductSerializer(self.product)

        self.assertEqual(
            serializer.data["category"]["name"],
            "Cakes",
        )

    def test_product_serializer_includes_images(self):
        ProductImage.objects.create(
            product=self.product,
            image="products/cake.jpg",
            alt_text="Chocolate cake",
            position=0,
        )

        serializer = ProductSerializer(self.product)

        self.assertEqual(len(serializer.data["images"]), 1)
        self.assertEqual(
            serializer.data["images"][0]["alt_text"],
            "Chocolate cake",
        )


class ProductAPITests(APITestCase):

    def setUp(self):
        self.category = Category.objects.create(
            name="Cakes",
            slug="cakes",
        )

        self.active_product = Product.objects.create(
            category=self.category,
            name="Chocolate Cake",
            slug="chocolate-cake",
            description="Rich chocolate cake.",
            price="250.00",
            sku="CAKE-001",
            is_active=True,
        )

        self.inactive_product = Product.objects.create(
            category=self.category,
            name="Old Cake",
            slug="old-cake",
            price="200.00",
            sku="CAKE-002",
            is_active=False,
        )

    def test_product_list_returns_active_products(self):
        url = reverse("product-list")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["name"],
            "Chocolate Cake",
        )

    def test_product_detail_returns_active_product(self):
        url = reverse(
            "product-detail",
            kwargs={"pk": self.active_product.pk},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["name"],
            "Chocolate Cake",
        )

    def test_inactive_product_is_not_publicly_accessible(self):
        url = reverse(
            "product-detail",
            kwargs={"pk": self.inactive_product.pk},
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_customer_cannot_create_product(self):
        url = reverse("product-list")

        response = self.client.post(
            url,
            {
                "name": "New Cake",
                "price": "300.00",
            },
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        )


