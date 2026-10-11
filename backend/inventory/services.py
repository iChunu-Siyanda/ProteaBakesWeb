from django.db import transaction

from .models import InventoryItem, InventoryMovement


def _locked_item(product_id):
    return (
        InventoryItem.objects
        .select_for_update()
        .filter(product_id=product_id)
        .first()
    )


@transaction.atomic
def restock_inventory(*, product_id, quantity, reference="", notes="", user=None):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    inventory = _locked_item(product_id)

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
        created_by=user,
    )

    return inventory, movement


@transaction.atomic
def remove_inventory(*, product_id, quantity, reference="", notes="", user=None):
    if quantity <= 0:
        raise ValueError("Quantity must be greater than zero.")

    inventory = _locked_item(product_id)

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
        created_by=user,
    )

    return inventory, movement


def is_tracked(product):
    """Made-to-order products and products without an InventoryItem are not stock-limited."""
    if product.is_made_to_order:
        return False
    return InventoryItem.objects.filter(product_id=product.id).exists()


def assert_available(product, quantity):
    """Raise ValueError if a stock-tracked product cannot supply ``quantity``."""
    if not is_tracked(product):
        return

    item = InventoryItem.objects.get(product_id=product.id)
    if item.quantity < quantity:
        if item.quantity == 0:
            raise ValueError(f"{product.name} is out of stock.")
        raise ValueError(f"Only {item.quantity} of {product.name} left in stock.")


@transaction.atomic
def reserve_stock_for_order(order):
    """Deduct stock for every stock-tracked line of ``order`` (SALE movements)."""
    for line in order.items.select_related("product"):
        if not is_tracked(line.product):
            continue
        try:
            remove_inventory(
                product_id=line.product_id,
                quantity=line.quantity,
                reference=order.order_number,
                notes="Reserved at checkout",
            )
        except ValueError:
            assert_available(line.product, line.quantity)
            raise


@transaction.atomic
def release_stock_for_order(order):
    """Return stock for a cancelled/expired order (RETURN movements). Idempotent."""
    sold = InventoryMovement.objects.filter(
        reference=order.order_number,
        movement_type=InventoryMovement.MovementType.SALE,
    ).select_related("inventory_item")

    already_returned = InventoryMovement.objects.filter(
        reference=order.order_number,
        movement_type=InventoryMovement.MovementType.RETURN,
    ).exists()

    if already_returned:
        return

    for movement in sold:
        item = (
            InventoryItem.objects
            .select_for_update()
            .get(pk=movement.inventory_item_id)
        )
        item.quantity += movement.quantity
        item.save(update_fields=["quantity", "updated_at"])

        InventoryMovement.objects.create(
            inventory_item=item,
            movement_type=InventoryMovement.MovementType.RETURN,
            quantity=movement.quantity,
            reference=order.order_number,
            notes="Order cancelled or expired",
        )
