from django.core.exceptions import ValidationError
from django.test import TestCase

from catalog.models import Category, Product
from inventory.models import InventoryMovement


class InventoryModelTests(TestCase):

    def setUp(self):
        category = Category.objects.create(
            name="Cakes",
            slug="cakes",
        )

        self.product = Product.objects.create(
            category=category,
            name="Chocolate Cake",
            slug="chocolate-cake",
            price="250.00",
            sku="CAKE-001",
        )

    def test_inventory_quantity_must_be_at_least_one(self):
        movement = InventoryMovement(
            product=self.product,
            movement_type=InventoryMovement.MovementType.PURCHASE,
            quantity=0,
        )

        with self.assertRaises(ValidationError):
            movement.full_clean()

    def test_positive_inventory_movement_can_be_created(self):
        movement = InventoryMovement.objects.create(
            product=self.product,
            movement_type=InventoryMovement.MovementType.PURCHASE,
            quantity=10,
        )

        self.assertEqual(movement.quantity, 10)
        