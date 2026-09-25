from django.db import transaction
from .models import InventoryItem, InventoryMovement


@transaction.atomic
def restock_inventory(*, product_id, quantity, reference="", notes=""):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    inventory = (
        InventoryItem.objects
        .select_for_update()
        .filter(product_id=product_id)
        .first()
    )

    if not inventory:
        raise ValueError("Inventory item not found.")

    inventory.quantity += quantity
    inventory.save(update_fields=["quantity", "updated_at"])

    movement = InventoryMovement.objects.create(
        inventory_item=inventory,
        movement_type=InventoryMovement.MovementType.RESTOCK,
        quantity=quantity,
        reference=reference,
        notes=notes,
    )

    return inventory, movement


@transaction.atomic
def remove_inventory(*, product_id, quantity, reference="", notes=""):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    inventory = (
        InventoryItem.objects
        .select_for_update()
        .filter(product_id=product_id)
        .first()
    )

    if not inventory:
        raise ValueError("Inventory item not found.")

    if inventory.quantity < quantity:
        raise ValueError("Insufficient inventory.")

    inventory.quantity -= quantity
    inventory.save(update_fields=["quantity", "updated_at"])

    movement = InventoryMovement.objects.create(
        inventory_item=inventory,
        movement_type=InventoryMovement.MovementType.SALE,
        quantity=quantity,
        reference=reference,
        notes=notes,
    )

    return inventory, movement
