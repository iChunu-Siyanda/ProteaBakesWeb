from rest_framework import serializers

from .models import Order, OrderItem, OrderStatusHistory
from .scheduling import validate_pickup_slot

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
    promotion_code = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=50,
    )

    def validate(self, attrs):
        fulfillment_type = attrs["fulfillment_type"]
        scheduled_date = attrs.get("scheduled_date")
        scheduled_time = attrs.get("scheduled_time")
        delivery_data = attrs.get("delivery_data")

        if fulfillment_type == Order.FulfillmentType.PICKUP:
            if scheduled_date and scheduled_time:
                error = validate_pickup_slot(scheduled_date, scheduled_time)
                if error:
                    raise serializers.ValidationError(
                        {"scheduled_date": error}
                    )

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


class StatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatusHistory
        fields = ["old_status", "new_status", "created_at"]
        read_only_fields = fields


class OrderDetailSerializer(OrderSerializer):
    """Full customer/staff view of an order, including fulfillment and payment."""

    fulfillment = serializers.SerializerMethodField()
    payment = serializers.SerializerMethodField()
    status_history = StatusHistorySerializer(many=True, read_only=True)

    class Meta(OrderSerializer.Meta):
        fields = OrderSerializer.Meta.fields + [
            "fulfillment",
            "payment",
            "status_history",
        ]

    def get_fulfillment(self, order):
        booking = getattr(order, "booking", None)
        if booking is not None:
            return {
                "type": "PICKUP",
                "status": booking.status,
                "scheduled_date": booking.scheduled_date,
                "scheduled_time": booking.scheduled_time,
            }

        delivery = getattr(order, "delivery", None)
        if delivery is not None:
            return {
                "type": "DELIVERY",
                "status": delivery.status,
                "recipient_name": delivery.recipient_name,
                "address_line_1": delivery.address_line_1,
                "address_line_2": delivery.address_line_2,
                "city": delivery.city,
                "province": delivery.province,
                "postal_code": delivery.postal_code,
                "tracking_reference": delivery.tracking_reference,
                "delivered_at": delivery.delivered_at,
            }

        return None

    def get_payment(self, order):
        payment = getattr(order, "payment", None)
        if payment is None:
            return None
        return {
            "status": payment.status,
            "amount": payment.amount,
            "currency": payment.currency,
            "paid_at": payment.paid_at,
        }


class StaffOrderSerializer(OrderDetailSerializer):
    customer_email = serializers.EmailField(source="user.email", read_only=True)
    customer_name = serializers.SerializerMethodField()
    customer_phone = serializers.CharField(source="user.phone_number", read_only=True)

    class Meta(OrderDetailSerializer.Meta):
        fields = OrderDetailSerializer.Meta.fields + [
            "customer_email",
            "customer_name",
            "customer_phone",
        ]

    def get_customer_name(self, order):
        return f"{order.user.first_name} {order.user.last_name}".strip()


class OrderStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Order.Status.choices)
