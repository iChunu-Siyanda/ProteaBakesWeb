from django.contrib import admin

from .models import Cart, CartItem


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "updated_at")
    list_filter = ("status",)
    search_fields = ("user__email",)
    inlines = [CartItemInline]
