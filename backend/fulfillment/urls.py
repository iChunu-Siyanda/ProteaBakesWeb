from django.urls import path

from .views import BookingUpdateView, DeliveryUpdateView, FulfillmentScheduleView

urlpatterns = [
    path("schedule/", FulfillmentScheduleView.as_view(), name="fulfillment-schedule"),
    path(
        "bookings/<int:booking_id>/",
        BookingUpdateView.as_view(),
        name="booking-update",
    ),
    path(
        "deliveries/<int:delivery_id>/",
        DeliveryUpdateView.as_view(),
        name="delivery-update",
    ),
]
