from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from orders.models import Order
from .services import redeem_promotion, validate_promotion
from .serializers import (
    PromotionRedeemSerializer,
    PromotionValidateSerializer,
)

class PromotionValidateView(APIView):
    permission_classes = [IsAuthenticated]


    def post(self, request):
        serializer = PromotionValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            promotion, discount = validate_promotion(
                code=serializer.validated_data["code"],
                user=request.user,
                order_total=serializer.validated_data["order_total"],
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "promotion": promotion.code,
                "discount": discount,
                "discount_type": promotion.discount_type,
            },
            status=status.HTTP_200_OK,
        )


class PromotionRedeemView(APIView):
    permission_classes = [IsAuthenticated]


    def post(self, request):
        serializer = PromotionRedeemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        order = (
            Order.objects
            .filter(
                id=serializer.validated_data["order_id"],
                user=request.user,
            )
            .first()
        )

        if not order:
            return Response(
                {"detail": "Order not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            promotion, discount = validate_promotion(
                code=serializer.validated_data["code"],
                user=request.user,
                order_total=order.subtotal,
            )

            redemption = redeem_promotion(
                promotion=promotion,
                user=request.user,
                order=order,
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "promotion": promotion.code,
                "discount": discount,
                "redemption_id": redemption.id,
            },
            status=status.HTTP_201_CREATED,
        )
