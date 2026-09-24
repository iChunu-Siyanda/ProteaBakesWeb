from django.db import models
from django.core.validators import MinValueValidator


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PROCESSING = "PROCESSING", "Processing"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"
        CANCELLED = "CANCELLED", "Cancelled"
        REFUNDED = "REFUNDED", "Refunded"
        PARTIALLY_REFUNDED = "PARTIALLY_REFUNDED", "Partially refunded"

    order = models.OneToOneField(
        "orders.Order",
        on_delete=models.PROTECT,
        related_name="payment",
    )

    provider = models.CharField(max_length=50)

    provider_reference = models.CharField(
        max_length=255,
        unique=True,
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    currency = models.CharField(
        max_length=3,
        default="ZAR",
    )

    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.PENDING,
    )

    paid_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.order.order_number} - {self.status}"


class PaymentTransaction(models.Model):
    class TransactionType(models.TextChoices):
        PAYMENT = "PAYMENT", "Payment"
        REFUND = "REFUND", "Refund"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"

    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name="transactions",
    )

    transaction_reference = models.CharField(
        max_length=255,
        unique=True,
    )

    transaction_type = models.CharField(
        max_length=20,
        choices=TransactionType.choices,
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.transaction_reference


class Refund(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCEEDED = "SUCCEEDED", "Succeeded"
        FAILED = "FAILED", "Failed"

    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name="refunds",
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    provider_reference = models.CharField(
        max_length=255,
        unique=True,
    )

    reason = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Refund - {self.provider_reference}"


class WebhookEvent(models.Model):
    provider = models.CharField(max_length=50)

    event_id = models.CharField(
        max_length=255,
        unique=True,
    )

    event_type = models.CharField(max_length=100)

    payload = models.JSONField()

    processed = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.provider} - {self.event_type}"
    