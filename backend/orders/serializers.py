from rest_framework import serializers
from .models import Order, OrderItem


class DeliveryDataSerializer(serializers.Serializer):
    recipient_name = serializers.CharField(max_length=200)
    phone_number = serializers.CharField(max_length=30)
    address_line_1 = serializers.CharField(max_length=255)
    address_line_2 = serializers.CharField(
        max_length=255,
        required=False,
        allow_blank=True,
    )
    city = serializers.CharField(max_length=100)
    province = serializers.CharField(max_length=100)
    postal_code = serializers.CharField(max_length=20)


class CheckoutSerializer(serializers.Serializer):
    fulfillment_type = serializers.ChoiceField(choices=Order.FulfillmentType.choices)
    customer_notes = serializers.CharField(required=False,allow_blank=True,)
    scheduled_date = serializers.DateField(required=False)
    scheduled_time = serializers.TimeField(required=False)
    delivery_data = DeliveryDataSerializer(required=False)

    def validate(self, attrs):
        fulfillment_type = attrs["fulfillment_type"]
        scheduled_date = attrs.get("scheduled_date")
        scheduled_time = attrs.get("scheduled_time")
        delivery_data = attrs.get("delivery_data")

        if fulfillment_type == Order.FulfillmentType.PICKUP:
            if not scheduled_date:
                raise serializers.ValidationError({
                    "scheduled_date": "A scheduled date is required for pickup orders."
                })

            if not scheduled_time:
                raise serializers.ValidationError({
                    "scheduled_time": "A scheduled time is required for pickup orders."
                })

        if fulfillment_type == Order.FulfillmentType.DELIVERY:
            if not delivery_data:
                raise serializers.ValidationError({
                        "delivery_data": (
                            "Delivery information is required "
                            "for delivery orders."
                        )
                })

            if scheduled_date or scheduled_time:
                raise serializers.ValidationError({
                    "scheduled_date": "Pickup scheduling cannot be used for delivery orders."
                })

        if (
            fulfillment_type == Order.FulfillmentType.PICKUP
            and delivery_data
        ):
            raise serializers.ValidationError(
                {
                    "delivery_data": (
                        "Delivery information cannot be provided "
                        "for pickup orders."
                    )
                }
            )

        if (
            fulfillment_type == Order.FulfillmentType.DELIVERY
            and scheduled_date
        ):
            raise serializers.ValidationError(
                {
                    "scheduled_date": (
                        "A scheduled date is only used "
                        "for pickup orders."
                    )
                }
            )

        return attrs
    

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product",
            "product_name",
            "unit_price",
            "quantity",
            "subtotal",
        ]


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "status",
            "fulfillment_type",
            "subtotal",
            "discount_amount",
            "delivery_fee",
            "total",
            "customer_notes",
            "items",
            "created_at",
            "updated_at",
        ]
        