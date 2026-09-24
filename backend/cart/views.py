from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    CartSerializer,
    CartItemCreateSerializer,
    CartItemUpdateSerializer,
    CartItemSerializer,
)
from .services import (
    get_or_create_active_cart,
    add_item_to_cart,
    update_cart_item,
    remove_cart_item,
)


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = get_or_create_active_cart(request.user)

        cart = (
            cart.__class__.objects
            .prefetch_related("items__product")
            .get(pk=cart.pk)
        )

        return Response(CartSerializer(cart).data)


class CartItemCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CartItemCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            item = add_item_to_cart(
                user=request.user,
                product_id=serializer.validated_data["product"],
                quantity=serializer.validated_data["quantity"],
            )
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Product does not exist or is inactive."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(
            CartItemSerializer(item).data,
            status=status.HTTP_201_CREATED,
        )


class CartItemUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, item_id):
        serializer = CartItemUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            item = update_cart_item(
                user=request.user,
                item_id=item_id,
                quantity=serializer.validated_data["quantity"],
            )
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Cart item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(CartItemSerializer(item).data)


class CartItemDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, item_id):
        try:
            remove_cart_item(
                user=request.user,
                item_id=item_id,
            )
        except ObjectDoesNotExist:
            return Response(
                {"detail": "Cart item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)
    