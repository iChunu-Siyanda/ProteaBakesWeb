from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import CheckoutSerializer, OrderSerializer
from .services import create_order


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
    