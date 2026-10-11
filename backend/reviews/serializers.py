from rest_framework import serializers

from .models import Review


class ReviewCreateSerializer(serializers.Serializer):
    order_item_id = serializers.IntegerField()
    product_id = serializers.IntegerField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
    )


class ReviewSerializer(serializers.ModelSerializer):
    """Public representation of a published review."""

    reviewer = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = ["id", "product", "rating", "comment", "reviewer", "created_at"]
        read_only_fields = fields

    def get_reviewer(self, review):
        # First name + last initial only; never expose email addresses.
        first = review.user.first_name or "Customer"
        last = review.user.last_name[:1]
        return f"{first} {last}." if last else first


class ReviewModerationSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[Review.Status.PUBLISHED, Review.Status.REJECTED]
    )


class StaffReviewSerializer(serializers.ModelSerializer):
    customer_email = serializers.EmailField(source="user.email", read_only=True)
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "product",
            "product_name",
            "customer_email",
            "rating",
            "comment",
            "status",
            "created_at",
        ]
        read_only_fields = fields
