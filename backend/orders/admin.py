from django.contrib import admin

from .models import Order, OrderItem, OrderStatusHistory


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("product", "product_name", "unit_price", "quantity", "subtotal")
    can_delete = False


class StatusHistoryInline(admin.TabularInline):
    model = OrderStatusHistory
    extra = 0
    readonly_fields = ("old_status", "new_status", "changed_by", "created_at")
    can_delete = False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Totals are read-only. Change status through the API (or the admin action
    below) so stock, fulfillment, notifications and the audit trail stay in sync.
    """

    list_display = ("order_number", "user", "status", "fulfillment_type", "total", "created_at")
    list_filter = ("status", "fulfillment_type")
    search_fields = ("order_number", "user__email")
    readonly_fields = (
        "order_number", "user", "status", "fulfillment_type", "subtotal",
        "discount_amount", "delivery_fee", "total", "created_at", "updated_at",
    )
    inlines = [OrderItemInline, StatusHistoryInline]
    actions = ["mark_preparing", "mark_ready", "mark_completed", "cancel_orders"]

    def _bulk(self, request, queryset, new_status):
        from .services import change_order_status

        done = 0
        for order in queryset:
            try:
                change_order_status(
                    order_id=order.id, new_status=new_status, changed_by=request.user
                )
                done += 1
            except ValueError as exc:
                self.message_user(request, f"{order.order_number}: {exc}", level="error")
        self.message_user(request, f"{done} order(s) updated.")

    @admin.action(description="Mark selected orders as preparing")
    def mark_preparing(self, request, queryset):
        self._bulk(request, queryset, Order.Status.PREPARING)

    @admin.action(description="Mark selected orders as ready")
    def mark_ready(self, request, queryset):
        self._bulk(request, queryset, Order.Status.READY)

    @admin.action(description="Mark selected orders as completed")
    def mark_completed(self, request, queryset):
        self._bulk(request, queryset, Order.Status.COMPLETED)

    @admin.action(description="Cancel selected orders")
    def cancel_orders(self, request, queryset):
        self._bulk(request, queryset, Order.Status.CANCELLED)

    def has_add_permission(self, request):
        return False
