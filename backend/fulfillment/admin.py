from django.contrib import admin

from .models import Booking, Delivery


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("order", "scheduled_date", "scheduled_time", "status")
    list_filter = ("status", "scheduled_date")
    search_fields = ("order__order_number",)


@admin.register(Delivery)
class DeliveryAdmin(admin.ModelAdmin):
    list_display = ("order", "recipient_name", "city", "status", "scheduled_date")
    list_filter = ("status", "province")
    search_fields = ("order__order_number", "recipient_name", "tracking_reference")
