from django.conf import settings
from django.db import models


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        ORDER_CONFIRMED = "ORDER_CONFIRMED", "Order confirmed"
        ORDER_PREPARING = "ORDER_PREPARING", "Order preparing"
        ORDER_READY = "ORDER_READY", "Order ready"
        ORDER_OUT_FOR_DELIVERY = "ORDER_OUT_FOR_DELIVERY", "Order out for delivery"
        ORDER_COMPLETED = "ORDER_COMPLETED", "Order completed"
        PAYMENT_SUCCEEDED = "PAYMENT_SUCCEEDED", "Payment succeeded"
        PAYMENT_FAILED = "PAYMENT_FAILED", "Payment failed"
        GENERAL = "GENERAL", "General"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    notification_type = models.CharField(
        max_length=50,
        choices=NotificationType.choices,
    )

    title = models.CharField(max_length=200)
    message = models.TextField()

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.email} - {self.title}"

# NotificationPreference controls how the customer wants to receive notifications.
class NotificationPreference(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notification_preferences",
    )

    email_enabled = models.BooleanField(default=True)
    sms_enabled = models.BooleanField(default=True)
    push_enabled = models.BooleanField(default=True)

    def __str__(self):
        return f"Notification preferences - {self.user.email}"
    