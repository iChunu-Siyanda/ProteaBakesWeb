from rest_framework import serializers

class PromotionValidateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    order_total = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=0,
    )

class PromotionRedeemSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    order_id = serializers.IntegerField()
