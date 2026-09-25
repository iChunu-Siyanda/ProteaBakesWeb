from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    InventoryRemoveSerializer,
    InventoryRestockSerializer,
)
from .services import remove_inventory, restock_inventory


class InventoryRestockView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = InventoryRestockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            inventory, movement = restock_inventory(
                product_id=serializer.validated_data["product_id"],
                quantity=serializer.validated_data["quantity"],
                reference=serializer.validated_data.get("reference", ""),
                notes=serializer.validated_data.get("notes", ""),
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "product_id": inventory.product_id,
                "quantity": inventory.quantity,
                "movement_id": movement.id,
                "movement_type": movement.movement_type,
            },
            status=status.HTTP_200_OK,
        )


class InventoryRemoveView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request):
        serializer = InventoryRemoveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            inventory, movement = remove_inventory(
                product_id=serializer.validated_data["product_id"],
                quantity=serializer.validated_data["quantity"],
                reference=serializer.validated_data.get("reference", ""),
                notes=serializer.validated_data.get("notes", ""),
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "product_id": inventory.product_id,
                "quantity": inventory.quantity,
                "movement_id": movement.id,
                "movement_type": movement.movement_type,
            },
            status=status.HTTP_200_OK,
        )
    