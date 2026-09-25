from rest_framework import serializers


class InventoryRestockSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    reference = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
    )


class InventoryRemoveSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1)
    reference = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=100,
    )
    notes = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    