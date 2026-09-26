from rest_framework import serializers

class ReviewCreateSerializer(serializers.Serializer):
    order_item_id = serializers.IntegerField()
    product_id = serializers.IntegerField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    comment = serializers.CharField(
        required=False,
        allow_blank=True,
    )
