from django.urls import path

from .views import (
    CheckoutView,
    OrderCancelView,
    OrderDetailView,
    OrderListView,
    StaffOrderListView,
    StaffOrderStatusView,
)

urlpatterns = [
    path("", OrderListView.as_view(), name="order-list"),
    path("checkout/", CheckoutView.as_view(), name="checkout"),
    path("staff/", StaffOrderListView.as_view(), name="staff-order-list"),
    path(
        "staff/<str:order_number>/status/",
        StaffOrderStatusView.as_view(),
        name="staff-order-status",
    ),
    path("<str:order_number>/", OrderDetailView.as_view(), name="order-detail"),
    path(
        "<str:order_number>/cancel/",
        OrderCancelView.as_view(),
        name="order-cancel",
    ),
]
