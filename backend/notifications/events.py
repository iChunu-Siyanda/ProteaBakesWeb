"""
Customer-facing notification events.

``notify_user`` always stores an in-app Notification and, if the customer has
email enabled, sends an email once the surrounding transaction commits. Email
failures are logged and never break the request that triggered them.
"""

import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction

from .models import Notification
from .services import create_notification, get_or_create_notification_preferences

logger = logging.getLogger(__name__)


def _send_email(to_address, subject, message):
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [to_address],
            fail_silently=False,
        )
    except Exception:  # noqa: BLE001 - never let email break an order flow
        logger.exception("Failed to send notification email to %s", to_address)


def notify_user(*, user, notification_type, title, message):
    notification = create_notification(
        user=user,
        notification_type=notification_type,
        title=title,
        message=message,
    )

    preferences = get_or_create_notification_preferences(user=user)
    if preferences.email_enabled and user.email:
        transaction.on_commit(
            lambda: _send_email(user.email, title, message)
        )

    return notification


ORDER_STATUS_NOTIFICATIONS = {
    "CONFIRMED": (
        Notification.NotificationType.ORDER_CONFIRMED,
        "Order confirmed",
        "Thank you! Order {order_number} is confirmed.",
    ),
    "PREPARING": (
        Notification.NotificationType.ORDER_PREPARING,
        "We're baking your order",
        "Order {order_number} is being prepared.",
    ),
    "READY": (
        Notification.NotificationType.ORDER_READY,
        "Your order is ready",
        "Order {order_number} is ready.",
    ),
    "OUT_FOR_DELIVERY": (
        Notification.NotificationType.ORDER_OUT_FOR_DELIVERY,
        "Your order is on its way",
        "Order {order_number} is out for delivery.",
    ),
    "COMPLETED": (
        Notification.NotificationType.ORDER_COMPLETED,
        "Order completed",
        "Order {order_number} is complete. Enjoy! We'd love a review.",
    ),
    "CANCELLED": (
        Notification.NotificationType.GENERAL,
        "Order cancelled",
        "Order {order_number} has been cancelled.",
    ),
}


def notify_order_status(order):
    entry = ORDER_STATUS_NOTIFICATIONS.get(order.status)
    if not entry:
        return None

    notification_type, title, template = entry
    return notify_user(
        user=order.user,
        notification_type=notification_type,
        title=title,
        message=template.format(order_number=order.order_number),
    )


def notify_payment_succeeded(payment):
    return notify_user(
        user=payment.order.user,
        notification_type=Notification.NotificationType.PAYMENT_SUCCEEDED,
        title="Payment received",
        message=(
            f"We received your payment of R{payment.amount} "
            f"for order {payment.order.order_number}."
        ),
    )


def notify_payment_failed(payment):
    return notify_user(
        user=payment.order.user,
        notification_type=Notification.NotificationType.PAYMENT_FAILED,
        title="Payment failed",
        message=(
            f"Your payment for order {payment.order.order_number} "
            "did not go through. You can try again from your orders page."
        ),
    )
