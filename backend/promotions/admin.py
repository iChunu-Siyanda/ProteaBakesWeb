from django.contrib import admin

from .models import CouponRedemption, Promotion


@admin.register(Promotion)
class PromotionAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "discount_type", "discount_value", "starts_at", "expires_at", "is_active")
    list_filter = ("discount_type", "is_active")
    search_fields = ("code", "name")


@admin.register(CouponRedemption)
class CouponRedemptionAdmin(admin.ModelAdmin):
    list_display = ("promotion", "user", "order", "redeemed_at")
    readonly_fields = ("promotion", "user", "order", "redeemed_at")
