from django.db import IntegrityError
from django.test import TestCase

from catalog.models import Category, Product
from cart.models import Cart, CartItem
from users.models import User


class CartModelTests(TestCase):

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

    def test_cart_item_quantity_must_be_at_least_one(self):
        cart = Cart.objects.create(user=self.user)

        item = CartItem(
            cart=cart,
            product=self.product,
            quantity=0,
        )

        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_same_product_cannot_be_added_twice_to_cart(self):
        cart = Cart.objects.create(user=self.user)

        CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=1,
        )

        with self.assertRaises(IntegrityError):
            CartItem.objects.create(
                cart=cart,
                product=self.product,
                quantity=2,
            )

    def test_user_can_have_only_one_active_cart(self):
        Cart.objects.create(
            user=self.user,
            status=Cart.Status.ACTIVE,
        )

        with self.assertRaises(IntegrityError):
            Cart.objects.create(
                user=self.user,
                status=Cart.Status.ACTIVE,
            )


from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from catalog.models import Category, Product
from users.models import User
from cart.models import Cart, CartItem


class CartAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="securepassword123",
            first_name="Jane",
            last_name="Doe",
        )

        self.other_user = User.objects.create_user(
            email="other@example.com",
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
            description="Chocolate cake",
            price="250.00",
            sku="CAKE-001",
            is_active=True,
        )

        self.inactive_product = Product.objects.create(
            category=self.category,
            name="Inactive Cake",
            slug="inactive-cake",
            description="Inactive cake",
            price="200.00",
            sku="CAKE-002",
            is_active=False,
        )

        self.client.force_authenticate(user=self.user)

    def test_authenticated_user_can_view_cart(self):
        url = reverse("cart")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["status"], "ACTIVE")
        self.assertEqual(response.data["items"], [])

    def test_unauthenticated_user_cannot_view_cart(self):
        self.client.force_authenticate(user=None)

        response = self.client.get(reverse("cart"))

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_user_can_add_product_to_cart(self):
        url = reverse("cart-item-create")

        response = self.client.post(
            url,
            {
                "product": self.product.id,
                "quantity": 2,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(response.data["quantity"], 2)

        item = CartItem.objects.get(
            cart__user=self.user,
            product=self.product,
        )

        self.assertEqual(item.quantity, 2)

    def test_adding_same_product_increases_quantity(self):
        url = reverse("cart-item-create")

        self.client.post(
            url,
            {
                "product": self.product.id,
                "quantity": 2,
            },
            format="json",
        )

        response = self.client.post(
            url,
            {
                "product": self.product.id,
                "quantity": 3,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(response.data["quantity"], 5)

    def test_inactive_product_cannot_be_added(self):
        url = reverse("cart-item-create")

        response = self.client.post(
            url,
            {
                "product": self.inactive_product.id,
                "quantity": 1,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_quantity_must_be_at_least_one(self):
        url = reverse("cart-item-create")

        response = self.client.post(
            url,
            {
                "product": self.product.id,
                "quantity": 0,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_user_can_update_cart_item(self):
        cart = Cart.objects.create(user=self.user)

        item = CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=2,
        )

        url = reverse(
            "cart-item-update",
            kwargs={"item_id": item.id},
        )

        response = self.client.patch(
            url,
            {"quantity": 5},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(response.data["quantity"], 5)

        item.refresh_from_db()
        self.assertEqual(item.quantity, 5)

    def test_user_can_delete_cart_item(self):
        cart = Cart.objects.create(user=self.user)

        item = CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=2,
        )

        url = reverse(
            "cart-item-delete",
            kwargs={"item_id": item.id},
        )

        response = self.client.delete(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_204_NO_CONTENT,
        )
        self.assertFalse(
            CartItem.objects.filter(id=item.id).exists()
        )

    def test_user_cannot_modify_another_users_cart_item(self):
        other_cart = Cart.objects.create(
            user=self.other_user,
        )

        item = CartItem.objects.create(
            cart=other_cart,
            product=self.product,
            quantity=2,
        )

        url = reverse(
            "cart-item-update",
            kwargs={"item_id": item.id},
        )

        response = self.client.patch(
            url,
            {"quantity": 99},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        item.refresh_from_db()
        self.assertEqual(item.quantity, 2)
           
