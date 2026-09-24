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
            