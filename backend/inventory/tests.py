from django.core.exceptions import ValidationError
from django.test import TestCase

from catalog.models import Category, Product
from inventory.models import InventoryItem, InventoryMovement


class InventoryModelTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Cakes",
            slug="cakes",
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Chocolate Cake",
            slug="chocolate-cake",
            price="250.00",
            sku="CAKE-001",
        )

        self.inventory = InventoryItem.objects.create(
            product=self.product,
            quantity=10,
            low_stock_threshold=5,
        )

    def test_inventory_item_is_created(self):
        self.assertEqual(self.inventory.product, self.product)
        self.assertEqual(self.inventory.quantity, 10)
        self.assertEqual(self.inventory.low_stock_threshold, 5)

    def test_inventory_item_has_one_product(self):
        with self.assertRaises(Exception):
            InventoryItem.objects.create(
                product=self.product,
                quantity=20,
            )

    def test_inventory_quantity_cannot_be_negative(self):
        inventory = InventoryItem(
            product=self.product,
            quantity=-1,
        )

        with self.assertRaises(ValidationError):
            inventory.full_clean()

    def test_low_stock_threshold_cannot_be_negative(self):
        inventory = InventoryItem(
            product=self.product,
            quantity=10,
            low_stock_threshold=-1,
        )

        with self.assertRaises(ValidationError):
            inventory.full_clean()

    def test_inventory_movement_is_created(self):
        movement = InventoryMovement.objects.create(
            inventory_item=self.inventory,
            movement_type=InventoryMovement.MovementType.RESTOCK,
            quantity=10,
            reference="RESTOCK-001",
            notes="Initial stock",
        )

        self.assertEqual(movement.inventory_item, self.inventory)
        self.assertEqual(
            movement.movement_type,
            InventoryMovement.MovementType.RESTOCK,
        )
        self.assertEqual(movement.quantity, 10)

    def test_inventory_movement_quantity_must_be_positive(self):
        movement = InventoryMovement(
            inventory_item=self.inventory,
            movement_type=InventoryMovement.MovementType.SALE,
            quantity=0,
        )

        with self.assertRaises(ValidationError):
            movement.full_clean()

    def test_inventory_movement_quantity_cannot_be_negative(self):
        movement = InventoryMovement(
            inventory_item=self.inventory,
            movement_type=InventoryMovement.MovementType.SALE,
            quantity=-5,
        )

        with self.assertRaises(ValidationError):
            movement.full_clean()

    def test_inventory_movement_belongs_to_inventory_item(self):
        movement = InventoryMovement.objects.create(
            inventory_item=self.inventory,
            movement_type=InventoryMovement.MovementType.SALE,
            quantity=2,
        )

        self.assertEqual(
            self.inventory.movements.count(),
            1,
        )

        self.assertEqual(
            self.inventory.movements.first(),
            movement,
        )


from decimal import Decimal
from inventory.services import remove_inventory, restock_inventory


class InventoryServiceTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name="Cakes",
            slug="cakes",
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Chocolate Cake",
            slug="chocolate-cake",
            price=Decimal("250.00"),
            sku="CAKE-001",
        )

        self.inventory = InventoryItem.objects.create(
            product=self.product,
            quantity=10,
            low_stock_threshold=5,
        )

    def test_restock_inventory_increases_quantity(self):
        inventory, movement = restock_inventory(
            product_id=self.product.id,
            quantity=5,
        )

        self.assertEqual(inventory.quantity, 15)
        self.assertEqual(movement.quantity, 5)
        self.assertEqual(
            movement.movement_type,
            InventoryMovement.MovementType.RESTOCK,
        )

    def test_restock_inventory_creates_movement(self):
        restock_inventory(
            product_id=self.product.id,
            quantity=5,
            reference="RESTOCK-001",
            notes="New stock",
        )

        movement = InventoryMovement.objects.get(
            reference="RESTOCK-001"
        )

        self.assertEqual(movement.inventory_item, self.inventory)
        self.assertEqual(movement.quantity, 5)
        self.assertEqual(movement.notes, "New stock")

    def test_restock_requires_positive_quantity(self):
        with self.assertRaisesMessage(
            ValueError,
            "Quantity must be greater than zero.",
        ):
            restock_inventory(
                product_id=self.product.id,
                quantity=0,
            )

    def test_restock_negative_quantity_is_rejected(self):
        with self.assertRaisesMessage(
            ValueError,
            "Quantity must be greater than zero.",
        ):
            restock_inventory(
                product_id=self.product.id,
                quantity=-5,
            )

    def test_restock_requires_existing_inventory(self):
        with self.assertRaisesMessage(
            ValueError,
            "Inventory item not found.",
        ):
            restock_inventory(
                product_id=999999,
                quantity=5,
            )

    def test_remove_inventory_decreases_quantity(self):
        inventory, movement = remove_inventory(
            product_id=self.product.id,
            quantity=4,
        )

        self.assertEqual(inventory.quantity, 6)
        self.assertEqual(movement.quantity, 4)
        self.assertEqual(
            movement.movement_type,
            InventoryMovement.MovementType.SALE,
        )

    def test_remove_inventory_creates_sale_movement(self):
        remove_inventory(
            product_id=self.product.id,
            quantity=3,
            reference="ORDER-001",
            notes="Customer purchase",
        )

        movement = InventoryMovement.objects.get(
            reference="ORDER-001"
        )

        self.assertEqual(movement.inventory_item, self.inventory)
        self.assertEqual(movement.quantity, 3)
        self.assertEqual(
            movement.movement_type,
            InventoryMovement.MovementType.SALE,
        )

    def test_remove_inventory_cannot_exceed_available_quantity(self):
        with self.assertRaisesMessage(
            ValueError,
            "Insufficient inventory.",
        ):
            remove_inventory(
                product_id=self.product.id,
                quantity=11,
            )

        self.inventory.refresh_from_db()

        self.assertEqual(self.inventory.quantity, 10)
        self.assertEqual(
            InventoryMovement.objects.count(),
            0,
        )

    def test_remove_inventory_requires_positive_quantity(self):
        with self.assertRaisesMessage(
            ValueError,
            "Quantity must be greater than zero.",
        ):
            remove_inventory(
                product_id=self.product.id,
                quantity=0,
            )

    def test_remove_inventory_negative_quantity_is_rejected(self):
        with self.assertRaisesMessage(
            ValueError,
            "Quantity must be greater than zero.",
        ):
            remove_inventory(
                product_id=self.product.id,
                quantity=-2,
            )

    def test_remove_inventory_requires_existing_inventory(self):
        with self.assertRaisesMessage(
            ValueError,
            "Inventory item not found.",
        ):
            remove_inventory(
                product_id=999999,
                quantity=1,
            )

    def test_restock_and_remove_preserve_correct_quantity(self):
        restock_inventory(
            product_id=self.product.id,
            quantity=10,
        )

        remove_inventory(
            product_id=self.product.id,
            quantity=7,
        )

        self.inventory.refresh_from_db()

        self.assertEqual(self.inventory.quantity, 13)
        self.assertEqual(
            InventoryMovement.objects.count(),
            2,
        )


from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from users.models import User


class InventoryAPITests(APITestCase):
    def setUp(self):
        self.admin = User.objects.create_user(
            email="admin@example.com",
            password="securepassword123",
            first_name="Admin",
            last_name="User",
            is_staff=True,
        )

        self.user = User.objects.create_user(
            email="customer@example.com",
            password="securepassword123",
            first_name="John",
            last_name="Doe",
        )

        self.category = Category.objects.create(
            name="Cakes",
            slug="cakes",
        )

        self.product = Product.objects.create(
            category=self.category,
            name="Chocolate Cake",
            slug="chocolate-cake",
            price=Decimal("250.00"),
            sku="CAKE-001",
        )

        self.inventory = InventoryItem.objects.create(
            product=self.product,
            quantity=10,
            low_stock_threshold=5,
        )

        self.restock_url = reverse("inventory-restock")
        self.remove_url = reverse("inventory-remove")

    def authenticate(self, user):
        self.client.force_authenticate(user=user)

    def test_unauthenticated_user_cannot_restock(self):
        response = self.client.post(
            self.restock_url,
            {
                "product_id": self.product.id,
                "quantity": 5,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_unauthenticated_user_cannot_remove_inventory(self):
        response = self.client.post(
            self.remove_url,
            {
                "product_id": self.product.id,
                "quantity": 5,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_non_staff_user_cannot_restock(self):
        self.authenticate(self.user)

        response = self.client.post(
            self.restock_url,
            {
                "product_id": self.product.id,
                "quantity": 5,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_non_staff_user_cannot_remove_inventory(self):
        self.authenticate(self.user)

        response = self.client.post(
            self.remove_url,
            {
                "product_id": self.product.id,
                "quantity": 5,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_admin_can_restock_inventory(self):
        self.authenticate(self.admin)

        response = self.client.post(
            self.restock_url,
            {
                "product_id": self.product.id,
                "quantity": 5,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["product_id"],
            self.product.id,
        )

        self.assertEqual(
            response.data["quantity"],
            15,
        )

        self.assertEqual(
            response.data["movement_type"],
            InventoryMovement.MovementType.RESTOCK,
        )

        self.inventory.refresh_from_db()

        self.assertEqual(
            self.inventory.quantity,
            15,
        )

        self.assertEqual(
            InventoryMovement.objects.count(),
            1,
        )

    def test_admin_can_remove_inventory(self):
        self.authenticate(self.admin)

        response = self.client.post(
            self.remove_url,
            {
                "product_id": self.product.id,
                "quantity": 4,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data["product_id"],
            self.product.id,
        )

        self.assertEqual(
            response.data["quantity"],
            6,
        )

        self.assertEqual(
            response.data["movement_type"],
            InventoryMovement.MovementType.SALE,
        )

        self.inventory.refresh_from_db()

        self.assertEqual(
            self.inventory.quantity,
            6,
        )

    def test_restock_requires_product_id(self):
        self.authenticate(self.admin)

        response = self.client.post(
            self.restock_url,
            {
                "quantity": 5,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn("product_id", response.data)

    def test_restock_requires_positive_quantity(self):
        self.authenticate(self.admin)

        response = self.client.post(
            self.restock_url,
            {
                "product_id": self.product.id,
                "quantity": 0,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn("quantity", response.data)

    def test_remove_requires_positive_quantity(self):
        self.authenticate(self.admin)

        response = self.client.post(
            self.remove_url,
            {
                "product_id": self.product.id,
                "quantity": 0,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn("quantity", response.data)

    def test_restock_unknown_product_returns_400(self):
        self.authenticate(self.admin)

        response = self.client.post(
            self.restock_url,
            {
                "product_id": 999999,
                "quantity": 5,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "Inventory item not found.",
        )

    def test_remove_unknown_product_returns_400(self):
        self.authenticate(self.admin)

        response = self.client.post(
            self.remove_url,
            {
                "product_id": 999999,
                "quantity": 5,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "Inventory item not found.",
        )

    def test_remove_more_than_available_returns_400(self):
        self.authenticate(self.admin)

        response = self.client.post(
            self.remove_url,
            {
                "product_id": self.product.id,
                "quantity": 11,
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertEqual(
            response.data["detail"],
            "Insufficient inventory.",
        )

        self.inventory.refresh_from_db()

        self.assertEqual(
            self.inventory.quantity,
            10,
        )

        self.assertEqual(
            InventoryMovement.objects.count(),
            0,
        )

    def test_restock_accepts_reference_and_notes(self):
        self.authenticate(self.admin)

        response = self.client.post(
            self.restock_url,
            {
                "product_id": self.product.id,
                "quantity": 5,
                "reference": "RESTOCK-001",
                "notes": "Fresh stock received",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        movement = InventoryMovement.objects.get(
            reference="RESTOCK-001"
        )

        self.assertEqual(
            movement.notes,
            "Fresh stock received",
        )

    def test_remove_accepts_reference_and_notes(self):
        self.authenticate(self.admin)

        response = self.client.post(
            self.remove_url,
            {
                "product_id": self.product.id,
                "quantity": 2,
                "reference": "ORDER-001",
                "notes": "Customer order",
            },
            format="json",
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        movement = InventoryMovement.objects.get(
            reference="ORDER-001"
        )

        self.assertEqual(
            movement.notes,
            "Customer order",
        )

    def test_restock_creates_movement(self):
        self.authenticate(self.admin)

        self.client.post(
            self.restock_url,
            {
                "product_id": self.product.id,
                "quantity": 5,
            },
            format="json",
        )

        movement = InventoryMovement.objects.get()

        self.assertEqual(
            movement.inventory_item,
            self.inventory,
        )

        self.assertEqual(
            movement.quantity,
            5,
        )

    def test_remove_creates_sale_movement(self):
        self.authenticate(self.admin)

        self.client.post(
            self.remove_url,
            {
                "product_id": self.product.id,
                "quantity": 3,
            },
            format="json",
        )

        movement = InventoryMovement.objects.get()

        self.assertEqual(
            movement.inventory_item,
            self.inventory,
        )

        self.assertEqual(
            movement.quantity,
            3,
        )

        self.assertEqual(
            movement.movement_type,
            InventoryMovement.MovementType.SALE,
        )

