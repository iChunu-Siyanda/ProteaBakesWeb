from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_audit_log

from .models import Booking, Delivery
from .serializers import (
    BookingSerializer,
    BookingUpdateSerializer,
    DeliverySerializer,
    DeliveryUpdateSerializer,
)
from orders.scheduling import validate_pickup_slot


class FulfillmentScheduleView(APIView):
    """
    Staff day sheet: pickups and deliveries for one day (?date=YYYY-MM-DD,
    default today), excluding cancelled ones.
    """

    permission_classes = [IsAdminUser]

    def get(self, request):
        raw = request.query_params.get("date")
        day = parse_date(raw) if raw else timezone.localdate()

        if day is None:
            return Response(
                {"detail": "Invalid date. Use YYYY-MM-DD."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        bookings = (
            Booking.objects
            .filter(scheduled_date=day)
            .exclude(status=Booking.Status.CANCELLED)
            .select_related("order", "order__user")
            .order_by("scheduled_time")
        )
        deliveries = (
            Delivery.objects
            .filter(scheduled_date=day)
            .exclude(status=Delivery.Status.CANCELLED)
            .select_related("order")
            .order_by("id")
        )

        return Response(
            {
                "date": day,
                "pickups": BookingSerializer(bookings, many=True).data,
                "deliveries": DeliverySerializer(deliveries, many=True).data,
            }
        )


class BookingUpdateView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def patch(self, request, booking_id):
        serializer = BookingUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        booking = (
            Booking.objects
            .select_for_update()
            .select_related("order", "order__user")
            .filter(id=booking_id)
            .first()
        )
        if not booking:
            return Response(
                {"detail": "Booking not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if booking.status in (Booking.Status.COMPLETED, Booking.Status.CANCELLED):
            return Response(
                {"detail": "This booking can no longer be changed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_date = data.get("scheduled_date", booking.scheduled_date)
        new_time = data.get("scheduled_time", booking.scheduled_time)

        if "scheduled_date" in data or "scheduled_time" in data:
            error = validate_pickup_slot(new_date, new_time)
            if error:
                return Response(
                    {"detail": error},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        old = {
            "scheduled_date": str(booking.scheduled_date),
            "scheduled_time": str(booking.scheduled_time),
        }
        booking.scheduled_date = new_date
        booking.scheduled_time = new_time
        if "notes" in data:
            booking.notes = data["notes"]
        booking.save()

        create_audit_log(
            action="BOOKING_UPDATED",
            user=request.user,
            model_name="Booking",
            object_id=booking.id,
            details={"old": old, "changed": list(data.keys())},
        )

        return Response(BookingSerializer(booking).data)


class DeliveryUpdateView(APIView):
    permission_classes = [IsAdminUser]

    @transaction.atomic
    def patch(self, request, delivery_id):
        serializer = DeliveryUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        delivery = (
            Delivery.objects
            .select_for_update()
            .select_related("order")
            .filter(id=delivery_id)
            .first()
        )
        if not delivery:
            return Response(
                {"detail": "Delivery not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        if delivery.status in (Delivery.Status.DELIVERED, Delivery.Status.CANCELLED):
            return Response(
                {"detail": "This delivery can no longer be changed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        for field in ("tracking_reference", "scheduled_date", "notes", "status"):
            if field in data:
                setattr(delivery, field, data[field])
        delivery.save()

        create_audit_log(
            action="DELIVERY_UPDATED",
            user=request.user,
            model_name="Delivery",
            object_id=delivery.id,
            details={"changed": list(data.keys())},
        )

        return Response(DeliverySerializer(delivery).data)
