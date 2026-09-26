from django.db import transaction

from .models import Notification, NotificationPreference


def create_notification(
    *,
    user,
    notification_type,
    title,
    message,
):
    return Notification.objects.create(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
    )


def get_user_notifications(*, user):
    return Notification.objects.filter(user=user).order_by("-created_at")


@transaction.atomic
def mark_notification_as_read(*, notification_id, user):
    notification = (
        Notification.objects
        .select_for_update()
        .filter(id=notification_id, user=user)
        .first()
    )

    if not notification:
        raise ValueError("Notification not found.")

    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=["is_read"])

    return notification


def get_or_create_notification_preferences(*, user):
    preferences, _ = NotificationPreference.objects.get_or_create(
        user=user
    )
    return preferences


@transaction.atomic
def update_notification_preferences(
    *,
    user,
    email_enabled=None,
    sms_enabled=None,
    push_enabled=None,
):
    preferences = get_or_create_notification_preferences(user=user)

    if email_enabled is not None:
        preferences.email_enabled = email_enabled

    if sms_enabled is not None:
        preferences.sms_enabled = sms_enabled

    if push_enabled is not None:
        preferences.push_enabled = push_enabled

    preferences.save()

    return preferences
