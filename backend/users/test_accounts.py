import re

from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import Address, User

ADDRESS = {
    "label": "Home",
    "recipient_name": "Jane Doe",
    "phone_number": "0821234567",
    "address_line_1": "1 Protea Street",
    "city": "Welkom",
    "province": "Free State",
    "postal_code": "9459",
}


class AccountTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="jane@example.com",
            password="correct-horse-battery",
            first_name="Jane",
            last_name="Doe",
        )

    def login(self):
        response = self.client.post(
            reverse("token-obtain"),
            {"email": "jane@example.com", "password": "correct-horse-battery"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response.data

    # --- registration -----------------------------------------------------

    def test_registration_rejects_common_passwords(self):
        response = self.client.post(
            reverse("user-register"),
            {
                "email": "new@example.com",
                "first_name": "New",
                "last_name": "User",
                "password": "password123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(User.objects.filter(email="new@example.com").exists())

    def test_registration_email_uniqueness_is_case_insensitive(self):
        response = self.client.post(
            reverse("user-register"),
            {
                "email": "JANE@example.com",
                "first_name": "Other",
                "last_name": "Jane",
                "password": "another-long-password-1",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- profile ----------------------------------------------------------

    def test_profile_can_be_updated_but_not_email(self):
        self.login()

        response = self.client.patch(
            reverse("user-profile"),
            {"first_name": "Janet", "email": "hacker@example.com"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Janet")
        self.assertEqual(self.user.email, "jane@example.com")

    # --- logout / password ------------------------------------------------

    def test_logout_blacklists_refresh_token(self):
        tokens = self.login()

        response = self.client.post(
            reverse("user-logout"), {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        refreshed = self.client.post(
            reverse("token-refresh"), {"refresh": tokens["refresh"]}, format="json"
        )
        self.assertEqual(refreshed.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_password_change_requires_current_password(self):
        self.login()

        bad = self.client.post(
            reverse("password-change"),
            {"current_password": "wrong", "new_password": "a-brand-new-passphrase"},
            format="json",
        )
        good = self.client.post(
            reverse("password-change"),
            {
                "current_password": "correct-horse-battery",
                "new_password": "a-brand-new-passphrase",
            },
            format="json",
        )

        self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(good.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("a-brand-new-passphrase"))

    def test_password_reset_flow(self):
        response = self.client.post(
            reverse("password-reset"), {"email": "JANE@example.com"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 1)

        match = re.search(r"uid=([^&\s]+)&token=([^\s]+)", mail.outbox[0].body)
        uid, token = match.groups()

        confirm = self.client.post(
            reverse("password-reset-confirm"),
            {"uid": uid, "token": token, "new_password": "totally-new-passphrase"},
            format="json",
        )

        self.assertEqual(confirm.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("totally-new-passphrase"))

        # The token is single-use: the password hash changed.
        again = self.client.post(
            reverse("password-reset-confirm"),
            {"uid": uid, "token": token, "new_password": "yet-another-passphrase"},
            format="json",
        )
        self.assertEqual(again.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_reset_does_not_reveal_unknown_emails(self):
        response = self.client.post(
            reverse("password-reset"), {"email": "nobody@example.com"}, format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mail.outbox), 0)

    def test_reset_with_bad_token_is_rejected(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))

        response = self.client.post(
            reverse("password-reset-confirm"),
            {"uid": uid, "token": "bad-token", "new_password": "totally-new-passphrase"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reset_token_helper_matches_real_token(self):
        # Guards the assumption the flow test relies on.
        self.assertTrue(
            default_token_generator.check_token(
                self.user, default_token_generator.make_token(self.user)
            )
        )

    # --- addresses --------------------------------------------------------

    def test_first_address_becomes_default_and_default_moves(self):
        self.login()

        first = self.client.post(reverse("address-list"), ADDRESS, format="json")
        second = self.client.post(
            reverse("address-list"),
            {**ADDRESS, "label": "Work", "is_default": True},
            format="json",
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertTrue(first.data["is_default"])
        self.assertEqual(second.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Address.objects.filter(user=self.user, is_default=True).count(), 1)
        self.assertTrue(Address.objects.get(label="Work").is_default)

    def test_address_update_and_delete(self):
        self.login()
        created = self.client.post(reverse("address-list"), ADDRESS, format="json")
        url = reverse("address-detail", kwargs={"pk": created.data["id"]})

        patched = self.client.patch(url, {"city": "Bloemfontein"}, format="json")
        deleted = self.client.delete(url)

        self.assertEqual(patched.data["city"], "Bloemfontein")
        self.assertEqual(deleted.status_code, status.HTTP_204_NO_CONTENT)

    def test_cannot_touch_another_users_address(self):
        other = User.objects.create_user(email="o@example.com", password="x-long-passphrase-1")
        theirs = Address.objects.create(user=other, **ADDRESS)
        self.login()

        listing = self.client.get(reverse("address-list"))
        detail = self.client.get(reverse("address-detail", kwargs={"pk": theirs.pk}))

        self.assertEqual(len(listing.data), 0)
        self.assertEqual(detail.status_code, status.HTTP_404_NOT_FOUND)
