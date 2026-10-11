from django.contrib import admin

from .models import InventoryItem, InventoryMovement


@admin.register(InventoryItem)
class InventoryItemAdmin(admin.ModelAdmin):
    list_display = ("product", "quantity", "low_stock_threshold", "updated_at")
    search_fields = ("product__name", "product__sku")
    # Change stock through the restock/remove endpoints so movements are recorded.
    readonly_fields = ("quantity",)


@admin.register(InventoryMovement)
class InventoryMovementAdmin(admin.ModelAdmin):
    list_display = ("inventory_item", "movement_type", "quantity", "reference", "created_by", "created_at")
    list_filter = ("movement_type",)
    search_fields = ("reference", "inventory_item__product__name")
    readonly_fields = ("inventory_item", "movement_type", "quantity", "reference", "created_by", "created_at")
