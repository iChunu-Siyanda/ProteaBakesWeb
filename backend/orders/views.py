from django.db.models import Q
from rest_framework import status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from config.pagination import StandardPagination

from .models import Order
from .serializers import (
    CheckoutSerializer,
    OrderDetailSerializer,
    OrderSerializer,
    OrderStatusUpdateSerializer,
    StaffOrderSerializer,
)
from .services import (
    cancel_order_for_customer,
    change_order_status,
    create_order,
)


def _order_queryset():
    return (
        Order.objects
        .select_related("user", "booking", "delivery", "payment")
        .prefetch_related("items", "status_history")
    )


class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            order = create_order(
                user=request.user,
                fulfillment_type=serializer.validated_data["fulfillment_type"],
                customer_notes=serializer.validated_data.get(
                    "customer_notes",
                    "",
                ),
                delivery_data=serializer.validated_data.get("delivery_data"),
                scheduled_date=serializer.validated_data.get("scheduled_date"),
                scheduled_time=serializer.validated_data.get("scheduled_time"),
                promotion_code=serializer.validated_data.get("promotion_code") or None,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )


class OrderListView(ListAPIView):
    """The signed-in customer's orders, newest first."""

    permission_classes = [IsAuthenticated]
    serializer_class = OrderSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        return (
            Order.objects
            .filter(user=self.request.user)
            .prefetch_related("items")
            .order_by("-created_at")
        )


class OrderDetailView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = OrderDetailSerializer
    lookup_field = "order_number"

    def get_queryset(self):
        return _order_queryset().filter(user=self.request.user)


class OrderCancelView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, order_number):
        try:
            order = cancel_order_for_customer(
                user=request.user,
                order_number=order_number,
            )
        except LookupError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_404_NOT_FOUND,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order = _order_queryset().get(pk=order.pk)
        return Response(OrderDetailSerializer(order).data)


# ---------------------------------------------------------------------------
# Staff
# ---------------------------------------------------------------------------


class StaffOrderListView(ListAPIView):
    """
    Staff order queue. Filters: ?status=CONFIRMED&fulfillment_type=PICKUP
    &date=YYYY-MM-DD (pickup/delivery date) &search=<order number or email>
    """

    permission_classes = [IsAdminUser]
    serializer_class = StaffOrderSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        qs = _order_queryset().order_by("-created_at")
        params = self.request.query_params

        if params.get("status"):
            qs = qs.filter(status=params["status"].upper())

        if params.get("fulfillment_type"):
            qs = qs.filter(fulfillment_type=params["fulfillment_type"].upper())

        if params.get("date"):
            qs = qs.filter(
                Q(booking__scheduled_date=params["date"])
                | Q(delivery__scheduled_date=params["date"])
            )

        if params.get("search"):
            term = params["search"]
            qs = qs.filter(
                Q(order_number__icontains=term) | Q(user__email__icontains=term)
            )

        return qs


class StaffOrderStatusView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, order_number):
        serializer = OrderStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = Order.objects.filter(order_number=order_number).first()
        if not order:
            return Response(
                {"detail": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            order = change_order_status(
                order_id=order.id,
                new_status=serializer.validated_data["status"],
                changed_by=request.user,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order = _order_queryset().get(pk=order.pk)
        return Response(StaffOrderSerializer(order).data)
