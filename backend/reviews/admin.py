from django.contrib import admin

from .models import Review


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("product", "user", "rating", "status", "created_at")
    list_filter = ("status", "rating")
    search_fields = ("product__name", "user__email", "comment")
    actions = ["publish", "reject"]

    @admin.action(description="Publish selected reviews")
    def publish(self, request, queryset):
        queryset.update(status=Review.Status.PUBLISHED)

    @admin.action(description="Reject selected reviews")
    def reject(self, request, queryset):
        queryset.update(status=Review.Status.REJECTED)
