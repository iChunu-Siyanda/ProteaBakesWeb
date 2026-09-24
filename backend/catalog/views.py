from rest_framework import viewsets

from .models import Product
from .serializers import ProductSerializer


class ProductViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ProductSerializer

    def get_queryset(self):
        return (
            Product.objects
            .filter(is_active=True)
            .select_related("category")
            .prefetch_related("images")
            .order_by("name")
        )
    