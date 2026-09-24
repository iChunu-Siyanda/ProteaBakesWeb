from django.db import IntegrityError
from django.test import TestCase

from users.models import User, Address


class UserModelTests(TestCase):

    def test_user_can_be_created_with_email(self):
        user = User.objects.create_user(
            email="customer@example.com",
            password="securepassword123",
            first_name="John",
            last_name="Doe",
        )

        self.assertEqual(user.email, "customer@example.com")
        self.assertTrue(user.check_password("securepassword123"))

    def test_email_must_be_unique(self):
        User.objects.create_user(
            email="customer@example.com",
            password="securepassword123",
            first_name="John",
            last_name="Doe",
        )

        with self.assertRaises(IntegrityError):
            User.objects.create_user(
                email="customer@example.com",
                password="anotherpassword123",
                first_name="Jane",
                last_name="Doe",
            )

    def test_only_one_default_address_per_user(self):
        user = User.objects.create_user(
            email="customer@example.com",
            password="securepassword123",
            first_name="John",
            last_name="Doe",
        )

        Address.objects.create(
            user=user,
            label="Home",
            recipient_name="John Doe",
            phone_number="0123456789",
            address_line_1="123 Main Street",
            city="Welkom",
            province="Free State",
            postal_code="9460",
            is_default=True,
        )

        with self.assertRaises(IntegrityError):
            Address.objects.create(
                user=user,
                label="Work",
                recipient_name="John Doe",
                phone_number="0123456789",
                address_line_1="456 Office Street",
                city="Welkom",
                province="Free State",
                postal_code="9460",
                is_default=True,
            )
            