from django.test import TestCase

from users.models import User

from notifications.models import Notification, NotificationPreference
from notifications.services import (
    create_notification,
    get_or_create_notification_preferences,
    get_user_notifications,
    mark_notification_as_read,
    update_notification_preferences,
)


class NotificationServiceTests(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="testpassword123",
        )

        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="testpassword123",
        )

    def test_create_notification(self):
        notification = create_notification(
            user=self.user,
            notification_type=Notification.NotificationType.ORDER_CONFIRMED,
            title="Order confirmed",
            message="Your order has been confirmed.",
        )

        self.assertEqual(notification.user, self.user)
        self.assertEqual(
            notification.notification_type,
            Notification.NotificationType.ORDER_CONFIRMED,
        )
        self.assertEqual(notification.title, "Order confirmed")
        self.assertEqual(
            notification.message,
            "Your order has been confirmed.",
        )
        self.assertFalse(notification.is_read)

    def test_create_notification_starts_unread(self):
        notification = create_notification(
            user=self.user,
            notification_type=Notification.NotificationType.GENERAL,
            title="Welcome",
            message="Welcome to Protea Bakes.",
        )

        self.assertFalse(notification.is_read)

    def test_get_user_notifications_returns_only_users_notifications(self):
        user_notification = Notification.objects.create(
            user=self.user,
            notification_type=Notification.NotificationType.GENERAL,
            title="User notification",
            message="For user.",
        )

        Notification.objects.create(
            user=self.other_user,
            notification_type=Notification.NotificationType.GENERAL,
            title="Other notification",
            message="For other user.",
        )

        notifications = get_user_notifications(user=self.user)

        self.assertEqual(notifications.count(), 1)
        self.assertEqual(notifications.first(), user_notification)

    def test_get_user_notifications_returns_newest_first(self):
        first = Notification.objects.create(
            user=self.user,
            notification_type=Notification.NotificationType.GENERAL,
            title="First",
            message="First message.",
        )

        second = Notification.objects.create(
            user=self.user,
            notification_type=Notification.NotificationType.GENERAL,
            title="Second",
            message="Second message.",
        )

        notifications = list(
            get_user_notifications(user=self.user)
        )

        self.assertEqual(notifications[0], second)
        self.assertEqual(notifications[1], first)

    def test_mark_notification_as_read(self):
        notification = Notification.objects.create(
            user=self.user,
            notification_type=Notification.NotificationType.ORDER_READY,
            title="Order ready",
            message="Your order is ready.",
        )

        self.assertFalse(notification.is_read)

        result = mark_notification_as_read(
            notification_id=notification.id,
            user=self.user,
        )

        notification.refresh_from_db()

        self.assertEqual(result, notification)
        self.assertTrue(notification.is_read)

    def test_mark_notification_as_read_is_idempotent(self):
        notification = Notification.objects.create(
            user=self.user,
            notification_type=Notification.NotificationType.GENERAL,
            title="Test",
            message="Test message.",
            is_read=True,
        )

        result = mark_notification_as_read(
            notification_id=notification.id,
            user=self.user,
        )

        notification.refresh_from_db()

        self.assertTrue(notification.is_read)
        self.assertEqual(result.id, notification.id)

    def test_user_cannot_mark_other_users_notification_as_read(self):
        notification = Notification.objects.create(
            user=self.other_user,
            notification_type=Notification.NotificationType.GENERAL,
            title="Private",
            message="Private notification.",
        )

        with self.assertRaisesMessage(
            ValueError,
            "Notification not found.",
        ):
            mark_notification_as_read(
                notification_id=notification.id,
                user=self.user,
            )

        notification.refresh_from_db()
        self.assertFalse(notification.is_read)

    def test_mark_nonexistent_notification_as_read(self):
        with self.assertRaisesMessage(
            ValueError,
            "Notification not found.",
        ):
            mark_notification_as_read(
                notification_id=999999,
                user=self.user,
            )

    def test_get_or_create_notification_preferences_creates_preferences(self):
        self.assertFalse(
            NotificationPreference.objects.filter(
                user=self.user
            ).exists()
        )

        preferences = get_or_create_notification_preferences(
            user=self.user
        )

        self.assertEqual(preferences.user, self.user)
        self.assertTrue(preferences.email_enabled)
        self.assertTrue(preferences.sms_enabled)
        self.assertTrue(preferences.push_enabled)

        self.assertTrue(
            NotificationPreference.objects.filter(
                user=self.user
            ).exists()
        )

    def test_get_or_create_notification_preferences_returns_existing(self):
        existing = NotificationPreference.objects.create(
            user=self.user,
            email_enabled=False,
            sms_enabled=True,
            push_enabled=False,
        )

        preferences = get_or_create_notification_preferences(
            user=self.user
        )

        self.assertEqual(preferences.id, existing.id)
        self.assertFalse(preferences.email_enabled)
        self.assertTrue(preferences.sms_enabled)
        self.assertFalse(preferences.push_enabled)

        self.assertEqual(
            NotificationPreference.objects.filter(
                user=self.user
            ).count(),
            1,
        )

    def test_update_notification_preferences(self):
        preferences = update_notification_preferences(
            user=self.user,
            email_enabled=False,
            sms_enabled=False,
            push_enabled=False,
        )

        preferences.refresh_from_db()

        self.assertFalse(preferences.email_enabled)
        self.assertFalse(preferences.sms_enabled)
        self.assertFalse(preferences.push_enabled)

    def test_update_notification_preferences_can_update_individual_settings(self):
        NotificationPreference.objects.create(
            user=self.user,
            email_enabled=True,
            sms_enabled=True,
            push_enabled=True,
        )

        preferences = update_notification_preferences(
            user=self.user,
            email_enabled=False,
        )

        preferences.refresh_from_db()

        self.assertFalse(preferences.email_enabled)
        self.assertTrue(preferences.sms_enabled)
        self.assertTrue(preferences.push_enabled)

    def test_update_notification_preferences_creates_preferences_if_missing(self):
        preferences = update_notification_preferences(
            user=self.user,
            sms_enabled=False,
        )

        self.assertFalse(preferences.sms_enabled)
        self.assertTrue(preferences.email_enabled)
        self.assertTrue(preferences.push_enabled)

        self.assertTrue(
            NotificationPreference.objects.filter(
                user=self.user
            ).exists()
        )


from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class NotificationAPITests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            email="user@example.com",
            password="testpassword123",
        )

        self.other_user = User.objects.create_user(
            email="other@example.com",
            password="testpassword123",
        )

        self.list_url = reverse("notification-list")
        self.preferences_url = reverse(
            "notification-preferences"
        )

    def authenticate(self):
        self.client.force_authenticate(user=self.user)

    def create_notification(
        self,
        user=None,
        notification_type=Notification.NotificationType.GENERAL,
        title="Test notification",
        message="Test message.",
        is_read=False,
    ):
        return Notification.objects.create(
            user=user or self.user,
            notification_type=notification_type,
            title=title,
            message=message,
            is_read=is_read,
        )

    # ---------------------------------------------------------
    # Notification list
    # ---------------------------------------------------------

    def test_unauthenticated_user_cannot_list_notifications(self):
        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_authenticated_user_can_list_notifications(self):
        self.authenticate()

        notification = self.create_notification()

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["id"], notification.id)

    def test_user_only_sees_their_own_notifications(self):
        self.authenticate()

        own_notification = self.create_notification()

        self.create_notification(
            user=self.other_user,
            title="Other user's notification",
        )

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["id"],
            own_notification.id,
        )

    def test_notification_list_contains_expected_fields(self):
        self.authenticate()

        self.create_notification(
            notification_type=Notification.NotificationType.ORDER_CONFIRMED,
            title="Order confirmed",
            message="Your order has been confirmed.",
        )

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        notification = response.data[0]

        self.assertIn("id", notification)
        self.assertIn("notification_type", notification)
        self.assertIn("title", notification)
        self.assertIn("message", notification)
        self.assertIn("is_read", notification)
        self.assertIn("created_at", notification)

    def test_notification_list_is_newest_first(self):
        self.authenticate()

        first = self.create_notification(
            title="First",
        )

        second = self.create_notification(
            title="Second",
        )

        response = self.client.get(self.list_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data[0]["id"],
            second.id,
        )
        self.assertEqual(
            response.data[1]["id"],
            first.id,
        )

    # ---------------------------------------------------------
    # Mark notification as read
    # ---------------------------------------------------------

    def test_unauthenticated_user_cannot_mark_notification_as_read(self):
        notification = self.create_notification()

        url = reverse(
            "notification-read",
            kwargs={"notification_id": notification.id},
        )

        response = self.client.post(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_authenticated_user_can_mark_notification_as_read(self):
        self.authenticate()

        notification = self.create_notification()

        url = reverse(
            "notification-read",
            kwargs={"notification_id": notification.id},
        )

        response = self.client.post(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        notification.refresh_from_db()

        self.assertTrue(notification.is_read)
        self.assertEqual(
            response.data["id"],
            notification.id,
        )
        self.assertTrue(response.data["is_read"])

    def test_marking_already_read_notification_is_idempotent(self):
        self.authenticate()

        notification = self.create_notification(
            is_read=True,
        )

        url = reverse(
            "notification-read",
            kwargs={"notification_id": notification.id},
        )

        response = self.client.post(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        notification.refresh_from_db()

        self.assertTrue(notification.is_read)

    def test_user_cannot_mark_other_users_notification_as_read(self):
        self.authenticate()

        notification = self.create_notification(
            user=self.other_user,
        )

        url = reverse(
            "notification-read",
            kwargs={"notification_id": notification.id},
        )

        response = self.client.post(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

        notification.refresh_from_db()

        self.assertFalse(notification.is_read)

    def test_mark_nonexistent_notification_as_read_returns_404(self):
        self.authenticate()

        url = reverse(
            "notification-read",
            kwargs={"notification_id": 999999},
        )

        response = self.client.post(url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )

    # ---------------------------------------------------------
    # Notification preferences - GET
    # ---------------------------------------------------------

    def test_unauthenticated_user_cannot_get_preferences(self):
        response = self.client.get(self.preferences_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_get_preferences_creates_default_preferences(self):
        self.authenticate()

        response = self.client.get(
            self.preferences_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data,
            {
                "email_enabled": True,
                "sms_enabled": True,
                "push_enabled": True,
            },
        )

        self.assertTrue(
            NotificationPreference.objects.filter(
                user=self.user
            ).exists()
        )

    def test_get_existing_preferences(self):
        self.authenticate()

        NotificationPreference.objects.create(
            user=self.user,
            email_enabled=False,
            sms_enabled=True,
            push_enabled=False,
        )

        response = self.client.get(
            self.preferences_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data,
            {
                "email_enabled": False,
                "sms_enabled": True,
                "push_enabled": False,
            },
        )

    def test_user_gets_only_their_own_preferences(self):
        self.authenticate()

        NotificationPreference.objects.create(
            user=self.other_user,
            email_enabled=False,
            sms_enabled=False,
            push_enabled=False,
        )

        response = self.client.get(
            self.preferences_url
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data,
            {
                "email_enabled": True,
                "sms_enabled": True,
                "push_enabled": True,
            },
        )

        self.assertFalse(
            NotificationPreference.objects.get(
                user=self.other_user
            ).email_enabled
        )

    # ---------------------------------------------------------
    # Notification preferences - PATCH
    # ---------------------------------------------------------

    def test_unauthenticated_user_cannot_update_preferences(self):
        response = self.client.patch(
            self.preferences_url,
            {"email_enabled": False},
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_update_all_preferences(self):
        self.authenticate()

        response = self.client.patch(
            self.preferences_url,
            {
                "email_enabled": False,
                "sms_enabled": False,
                "push_enabled": False,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data,
            {
                "email_enabled": False,
                "sms_enabled": False,
                "push_enabled": False,
            },
        )

        preferences = NotificationPreference.objects.get(
            user=self.user
        )

        self.assertFalse(preferences.email_enabled)
        self.assertFalse(preferences.sms_enabled)
        self.assertFalse(preferences.push_enabled)

    def test_update_individual_preference(self):
        self.authenticate()

        response = self.client.patch(
            self.preferences_url,
            {
                "email_enabled": False,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertFalse(
            response.data["email_enabled"]
        )
        self.assertTrue(
            response.data["sms_enabled"]
        )
        self.assertTrue(
            response.data["push_enabled"]
        )

    def test_update_preferences_creates_preferences_if_missing(self):
        self.authenticate()

        self.assertFalse(
            NotificationPreference.objects.filter(
                user=self.user
            ).exists()
        )

        response = self.client.patch(
            self.preferences_url,
            {
                "sms_enabled": False,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        preferences = NotificationPreference.objects.get(
            user=self.user
        )

        self.assertTrue(preferences.email_enabled)
        self.assertFalse(preferences.sms_enabled)
        self.assertTrue(preferences.push_enabled)

    def test_preferences_reject_non_boolean_values(self):
        self.authenticate()

        response = self.client.patch(
            self.preferences_url,
            {
                "email_enabled": "not-a-boolean",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_user_cannot_update_other_users_preferences(self):
        self.authenticate()

        other_preferences = NotificationPreference.objects.create(
            user=self.other_user,
            email_enabled=True,
            sms_enabled=True,
            push_enabled=True,
        )

        response = self.client.patch(
            self.preferences_url,
            {
                "email_enabled": False,
                "sms_enabled": False,
                "push_enabled": False,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        other_preferences.refresh_from_db()

        self.assertTrue(other_preferences.email_enabled)
        self.assertTrue(other_preferences.sms_enabled)
        self.assertTrue(other_preferences.push_enabled)

