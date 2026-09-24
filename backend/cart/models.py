from django.conf import settings
from django.db import models

from catalog.models import Product


class Cart(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        ABANDONED = "ABANDONED", "Abandoned"
        CONVERTED = "CONVERTED", "Converted"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cart",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart - {self.user.email}"


class CartItem(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name="items",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT, # Protects product when referenced by a cart.
        related_name="cart_items",
    )
    quantity = models.PositiveIntegerField()

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product"],
                name="unique_product_per_cart",
            )
        ]

    def __str__(self):
        return f"{self.product.name} × {self.quantity}"
    