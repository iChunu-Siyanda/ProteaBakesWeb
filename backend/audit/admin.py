from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Audit logs are append-only."""

    list_display = ("created_at", "action", "model_name", "object_id", "user")
    list_filter = ("action", "model_name")
    search_fields = ("action", "object_id", "user__email")
    readonly_fields = ("user", "action", "model_name", "object_id", "details", "ip_address", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
