from django.urls import path

from .views import (
    ProductReviewListView,
    ReviewCreateView,
    ReviewModerateView,
    StaffReviewListView,
)

urlpatterns = [
    path("", ReviewCreateView.as_view(), name="review-create"),
    path(
        "product/<int:product_id>/",
        ProductReviewListView.as_view(),
        name="product-review-list",
    ),
    path("staff/", StaffReviewListView.as_view(), name="staff-review-list"),
    path(
        "<int:review_id>/moderate/",
        ReviewModerateView.as_view(),
        name="review-moderate",
    ),
]
