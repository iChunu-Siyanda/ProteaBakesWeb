from django.db.models import Avg, Count, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import Category, Product
from .serializers import CategorySerializer, ProductSerializer

ORDERING = {
    "name": "name",
    "price": "price",
    "-price": "-price",
    "newest": "-created_at",
}


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Public catalogue. Optional query params:
    ?category=<slug>  ?search=<text>  ?ordering=name|price|-price|newest
    """

    permission_classes = [AllowAny]
    serializer_class = ProductSerializer

    def get_queryset(self):
        published = Q(reviews__status="PUBLISHED")

        qs = (
            Product.objects
            .filter(is_active=True)
            .select_related("category", "inventory")
            .prefetch_related("images")
            .annotate(
                published_rating_avg=Avg("reviews__rating", filter=published),
                published_review_count=Count("reviews", filter=published),
            )
        )

        params = self.request.query_params

        if params.get("category"):
            qs = qs.filter(category__slug=params["category"])

        if params.get("search"):
            term = params["search"]
            qs = qs.filter(
                Q(name__icontains=term)
                | Q(description__icontains=term)
                | Q(category__name__icontains=term)
            )

        return qs.order_by(ORDERING.get(params.get("ordering"), "name"))

    @action(
        detail=False,
        methods=["get"],
        url_path=r"slug/(?P<slug>[-\w]+)",
        url_name="by-slug",
    )
    def by_slug(self, request, slug=None):
        product = get_object_or_404(self.get_queryset(), slug=slug)
        return Response(self.get_serializer(product).data)


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer
    queryset = Category.objects.filter(is_active=True).order_by("name")
