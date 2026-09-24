from django.urls import path

from .views import (
    CartView,
    CartItemCreateView,
    CartItemUpdateView,
    CartItemDeleteView,
)


urlpatterns = [
    path("", CartView.as_view(), name="cart"),
    path("items/", CartItemCreateView.as_view(), name="cart-item-create"),
    path("items/<int:item_id>/", CartItemUpdateView.as_view(), name="cart-item-update",),
    path("items/<int:item_id>/delete/", CartItemDeleteView.as_view(), name="cart-item-delete",),
]
