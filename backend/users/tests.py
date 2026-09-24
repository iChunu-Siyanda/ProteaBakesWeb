from django.db import IntegrityError
from django.test import TestCase
from rest_framework.test import APITestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User
from users.serializers import UserRegistrationSerializer
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


class UserRegistrationSerializerTests(APITestCase):

    def test_valid_registration(self):
        serializer = UserRegistrationSerializer(
            data={
                "email": "newuser@example.com",
                "first_name": "Jane",
                "last_name": "Doe",
                "phone_number": "0123456789",
                "password": "securepassword123",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

        user = serializer.save()

        self.assertEqual(user.email, "newuser@example.com")
        self.assertTrue(
            user.check_password("securepassword123")
        )

    def test_password_is_not_returned(self):
        serializer = UserRegistrationSerializer(
            data={
                "email": "newuser@example.com",
                "first_name": "Jane",
                "last_name": "Doe",
                "password": "securepassword123",
            }
        )

        self.assertTrue(serializer.is_valid(), serializer.errors)

        user = serializer.save()

        response_serializer = UserRegistrationSerializer(user)

        self.assertNotIn("password", response_serializer.data)


class UserRegistrationAPITests(APITestCase):

    def test_user_can_register(self):
        url = reverse("user-register")

        response = self.client.post(
            url,
            {
                "email": "newuser@example.com",
                "first_name": "Jane",
                "last_name": "Doe",
                "phone_number": "0123456789",
                "password": "securepassword123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertTrue(
            User.objects.filter(
                email="newuser@example.com"
            ).exists()
        )

        self.assertNotIn("password", response.data)

    def test_duplicate_email_is_rejected(self):
        User.objects.create_user(
            email="existing@example.com",
            password="securepassword123",
            first_name="John",
            last_name="Doe",
        )

        url = reverse("user-register")

        response = self.client.post(
            url,
            {
                "email": "existing@example.com",
                "first_name": "Jane",
                "last_name": "Doe",
                "password": "securepassword123",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

User = get_user_model()


class JWTLoginAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="login@example.com",
            password="securepassword123",
            first_name="Jane",
            last_name="Doe",
        )

    def test_user_can_login(self):
        url = reverse("token-obtain")

        response = self.client.post(
            url,
            {
                "email": "login@example.com",
                "password": "securepassword123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

    def test_invalid_password_is_rejected(self):
        url = reverse("token-obtain")

        response = self.client.post(
            url,
            {
                "email": "login@example.com",
                "password": "wrongpassword",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_nonexistent_user_is_rejected(self):
        url = reverse("token-obtain")

        response = self.client.post(
            url,
            {
                "email": "doesnotexist@example.com",
                "password": "securepassword123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_refresh_token_returns_new_access_token(self):
        login_url = reverse("token-obtain")
        refresh_url = reverse("token-refresh")

        login_response = self.client.post(
            login_url,
            {
                "email": "login@example.com",
                "password": "securepassword123",
            },
            format="json",
        )

        refresh_response = self.client.post(
            refresh_url,
            {
                "refresh": login_response.data["refresh"],
            },
            format="json",
        )

        self.assertEqual(refresh_response.status_code, status.HTTP_200_OK)
        self.assertIn("access", refresh_response.data)


class UserProfileAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="profile@example.com",
            password="securepassword123",
            first_name="Jane",
            last_name="Doe",
            phone_number="0123456789",
        )

    def test_authenticated_user_can_view_profile(self):
        login_url = reverse("token-obtain")

        login_response = self.client.post(
            login_url,
            {
                "email": "profile@example.com",
                "password": "securepassword123",
            },
            format="json",
        )

        access_token = login_response.data["access"]

        self.client.credentials(
            HTTP_AUTHORIZATION=f"Bearer {access_token}"
        )

        url = reverse("user-profile")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["email"], "profile@example.com")
        self.assertEqual(response.data["first_name"], "Jane")
        self.assertEqual(response.data["last_name"], "Doe")

    def test_unauthenticated_user_cannot_view_profile(self):
        url = reverse("user-profile")

        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

# registration + login + refresh + authenticated-user flow                        