from django.contrib import admin

from .models import Payment, PaymentTransaction, Refund, WebhookEvent


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("order", "provider", "amount", "currency", "status", "paid_at")
    list_filter = ("status", "provider")
    search_fields = ("order__order_number", "provider_reference")
    readonly_fields = ("order", "provider", "provider_reference", "amount", "currency", "paid_at")


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ("transaction_reference", "payment", "transaction_type", "amount", "status")
    list_filter = ("transaction_type", "status")


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ("payment", "amount", "status", "created_at")
    list_filter = ("status",)


@admin.register(WebhookEvent)
class WebhookEventAdmin(admin.ModelAdmin):
    list_display = ("event_id", "provider", "event_type", "processed", "created_at")
    list_filter = ("provider", "processed")
    readonly_fields = ("provider", "event_id", "event_type", "payload", "created_at")
