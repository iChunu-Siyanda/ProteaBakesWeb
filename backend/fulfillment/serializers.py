from rest_framework import serializers

from orders.scheduling import validate_pickup_slot

from .models import Booking, Delivery


class BookingSerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)
    customer_name = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = [
            "id",
            "order_number",
            "customer_name",
            "scheduled_date",
            "scheduled_time",
            "status",
            "notes",
        ]
        read_only_fields = ["id", "order_number", "customer_name", "status"]

    def get_customer_name(self, booking):
        user = booking.order.user
        return f"{user.first_name} {user.last_name}".strip()


class BookingUpdateSerializer(serializers.Serializer):
    """Staff may reschedule a pickup or add notes. Status follows the order."""

    scheduled_date = serializers.DateField(required=False)
    scheduled_time = serializers.TimeField(required=False)
    notes = serializers.CharField(required=False, allow_blank=True)


class DeliverySerializer(serializers.ModelSerializer):
    order_number = serializers.CharField(source="order.order_number", read_only=True)

    class Meta:
        model = Delivery
        fields = [
            "id",
            "order_number",
            "recipient_name",
            "recipient_phone",
            "address_line_1",
            "address_line_2",
            "city",
            "province",
            "postal_code",
            "status",
            "delivery_fee",
            "tracking_reference",
            "scheduled_date",
            "delivered_at",
            "notes",
        ]
        read_only_fields = fields


class DeliveryUpdateSerializer(serializers.Serializer):
    """
    Staff may set a tracking reference, schedule and notes, and mark an
    attempt as ASSIGNED or FAILED. OUT_FOR_DELIVERY / DELIVERED / CANCELLED
    follow the order status so the two can never disagree.
    """

    tracking_reference = serializers.CharField(
        required=False, allow_blank=True, max_length=100
    )
    scheduled_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=[Delivery.Status.ASSIGNED, Delivery.Status.FAILED],
        required=False,
    )

    def validate_tracking_reference(self, value):
        return value or None
