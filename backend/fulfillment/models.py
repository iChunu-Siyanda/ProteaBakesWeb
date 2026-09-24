from django.db import models
from django.core.validators import MinValueValidator

# Both Booking and Delivery are OneToOne with order
class Booking(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        CONFIRMED = "CONFIRMED", "Confirmed"
        COMPLETED = "COMPLETED", "Completed"
        CANCELLED = "CANCELLED", "Cancelled"

    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="booking",
    )

    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Booking - {self.order.order_number}"


class Delivery(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        ASSIGNED = "ASSIGNED", "Assigned"
        OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY", "Out for delivery"
        DELIVERED = "DELIVERED", "Delivered"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"

    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.CASCADE,
        related_name="delivery",
    )

    recipient_name = models.CharField(max_length=200)
    recipient_phone = models.CharField(max_length=30)

    address_line_1 = models.CharField(max_length=255)
    address_line_2 = models.CharField(max_length=255, blank=True)
    city = models.CharField(max_length=100)
    province = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=20)

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
    )

    delivery_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    tracking_reference = models.CharField(
        max_length=100,
        blank=True,
        unique=True,
        null=True,
    )

    scheduled_date = models.DateField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Delivery - {self.order.order_number}"
    