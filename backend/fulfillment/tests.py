from datetime import date, time, timedelta

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from audit.models import AuditLog
from fulfillment.models import Booking, Delivery
from orders.test_lifecycle import DELIVERY, Fixture
from orders.tests import PICKUP_DATE


class FulfillmentAPITests(Fixture, APITestCase):
    def setUp(self):
        self.make_fixture()

    def test_endpoints_are_staff_only(self):
        order = self.pickup_order()
        self.client.force_authenticate(user=self.user)

        schedule = self.client.get(reverse("fulfillment-schedule"))
        patch = self.client.patch(
            reverse("booking-update", kwargs={"booking_id": order.booking.id}),
            {"notes": "x"},
            format="json",
        )

        self.assertEqual(schedule.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(patch.status_code, status.HTTP_403_FORBIDDEN)

    def test_schedule_lists_the_days_pickups(self):
        order = self.pickup_order()
        self.client.force_authenticate(user=self.staff)

        response = self.client.get(reverse("fulfillment-schedule"), {"date": PICKUP_DATE})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["pickups"]), 1)
        self.assertEqual(response.data["pickups"][0]["order_number"], order.order_number)
        self.assertEqual(response.data["deliveries"], [])

    def test_schedule_rejects_bad_date(self):
        self.client.force_authenticate(user=self.staff)

        response = self.client.get(reverse("fulfillment-schedule"), {"date": "nope"})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_staff_can_reschedule_pickup_within_rules(self):
        order = self.pickup_order()
        new_day = date.fromisoformat(PICKUP_DATE) + timedelta(days=1)
        while new_day.weekday() == 6:
            new_day += timedelta(days=1)
        self.client.force_authenticate(user=self.staff)

        response = self.client.patch(
            reverse("booking-update", kwargs={"booking_id": order.booking.id}),
            {"scheduled_date": new_day.isoformat(), "scheduled_time": "11:30:00"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.booking.refresh_from_db()
        self.assertEqual(order.booking.scheduled_date, new_day)
        self.assertEqual(order.booking.scheduled_time, time(11, 30))
        self.assertTrue(AuditLog.objects.filter(action="BOOKING_UPDATED").exists())

    def test_reschedule_outside_hours_is_rejected(self):
        order = self.pickup_order()
        self.client.force_authenticate(user=self.staff)

        response = self.client.patch(
            reverse("booking-update", kwargs={"booking_id": order.booking.id}),
            {"scheduled_time": "23:00:00"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_completed_booking_cannot_be_changed(self):
        order = self.pickup_order()
        Booking.objects.filter(pk=order.booking.pk).update(status=Booking.Status.COMPLETED)
        self.client.force_authenticate(user=self.staff)

        response = self.client.patch(
            reverse("booking-update", kwargs={"booking_id": order.booking.id}),
            {"notes": "late"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_staff_can_set_tracking_reference_and_schedule_delivery(self):
        order = self.delivery_order()
        self.client.force_authenticate(user=self.staff)

        response = self.client.patch(
            reverse("delivery-update", kwargs={"delivery_id": order.delivery.id}),
            {"tracking_reference": "TRK-1", "scheduled_date": PICKUP_DATE},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["tracking_reference"], "TRK-1")

        schedule = self.client.get(reverse("fulfillment-schedule"), {"date": PICKUP_DATE})
        self.assertEqual(len(schedule.data["deliveries"]), 1)

    def test_delivery_status_cannot_be_forced_to_delivered(self):
        order = self.delivery_order()
        self.client.force_authenticate(user=self.staff)

        response = self.client.patch(
            reverse("delivery-update", kwargs={"delivery_id": order.delivery.id}),
            {"status": "DELIVERED"},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        order.delivery.refresh_from_db()
        self.assertEqual(order.delivery.status, Delivery.Status.PENDING)

    def test_blank_tracking_reference_is_stored_as_null(self):
        order = self.delivery_order()
        self.client.force_authenticate(user=self.staff)

        response = self.client.patch(
            reverse("delivery-update", kwargs={"delivery_id": order.delivery.id}),
            {"tracking_reference": ""},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.delivery.refresh_from_db()
        self.assertIsNone(order.delivery.tracking_reference)

    def test_unknown_ids_are_404(self):
        self.client.force_authenticate(user=self.staff)

        booking = self.client.patch(
            reverse("booking-update", kwargs={"booking_id": 9999}), {}, format="json"
        )
        delivery = self.client.patch(
            reverse("delivery-update", kwargs={"delivery_id": 9999}), {}, format="json"
        )

        self.assertEqual(booking.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(delivery.status_code, status.HTTP_404_NOT_FOUND)
