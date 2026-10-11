from rest_framework import serializers

from .models import Category, Product, ProductImage


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = [
            "id",
            "image",
            "alt_text",
            "position",
        ]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = [
            "id",
            "name",
            "slug",
        ]


class ProductSerializer(serializers.ModelSerializer):
    category = CategorySerializer(read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)
    is_available = serializers.SerializerMethodField()
    average_rating = serializers.SerializerMethodField()
    review_count = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "description",
            "price",
            "sku",
            "category",
            "images",
            "is_active",
            "is_made_to_order",
            "is_available",
            "average_rating",
            "review_count",
        ]

    def get_is_available(self, product):
        """Made-to-order and untracked products are always orderable."""
        if product.is_made_to_order:
            return True

        inventory = getattr(product, "inventory", None)
        if inventory is None:
            return True

        return inventory.quantity > 0

    def get_average_rating(self, product):
        if hasattr(product, "published_rating_avg"):
            value = product.published_rating_avg
        else:
            from django.db.models import Avg

            value = product.reviews.filter(status="PUBLISHED").aggregate(
                v=Avg("rating")
            )["v"]

        return round(float(value), 2) if value is not None else None

    def get_review_count(self, product):
        if hasattr(product, "published_review_count"):
            return product.published_review_count
        return product.reviews.filter(status="PUBLISHED").count()
