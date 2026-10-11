from rest_framework import status
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.services import create_audit_log
from config.pagination import StandardPagination

from .models import Review
from .serializers import (
    ReviewCreateSerializer,
    ReviewModerationSerializer,
    ReviewSerializer,
    StaffReviewSerializer,
)
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


class ProductReviewListView(ListAPIView):
    """Public: published reviews for one product, newest first."""

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = ReviewSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        return (
            Review.objects
            .filter(
                product_id=self.kwargs["product_id"],
                status=Review.Status.PUBLISHED,
            )
            .select_related("user")
            .order_by("-created_at")
        )


class StaffReviewListView(ListAPIView):
    """Moderation queue. ?status=PENDING (default) | PUBLISHED | REJECTED"""

    permission_classes = [IsAdminUser]
    serializer_class = StaffReviewSerializer
    pagination_class = StandardPagination

    def get_queryset(self):
        wanted = self.request.query_params.get("status", Review.Status.PENDING).upper()
        return (
            Review.objects
            .filter(status=wanted)
            .select_related("user", "product")
            .order_by("created_at")
        )


class ReviewModerateView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, review_id):
        serializer = ReviewModerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        review = Review.objects.filter(id=review_id).first()
        if not review:
            return Response(
                {"detail": "Review not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        old_status = review.status
        review.status = serializer.validated_data["status"]
        review.save(update_fields=["status", "updated_at"])

        create_audit_log(
            action="REVIEW_MODERATED",
            user=request.user,
            model_name="Review",
            object_id=review.id,
            details={"old": old_status, "new": review.status},
        )

        return Response(StaffReviewSerializer(review).data)
