from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import ReviewCreateSerializer
from .services import create_review

class ReviewCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            review = create_review(
                user=request.user,
                order_item_id=serializer.validated_data["order_item_id"],
                product_id=serializer.validated_data["product_id"],
                rating=serializer.validated_data["rating"],
                comment=serializer.validated_data.get("comment", ""),
            )
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "id": review.id,
                "product_id": review.product_id,
                "order_item_id": review.order_item_id,
                "rating": review.rating,
                "comment": review.comment,
                "status": review.status,
                "created_at": review.created_at,
            },
            status=status.HTTP_201_CREATED,
        )
