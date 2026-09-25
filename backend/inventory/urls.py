from django.urls import path

from .views import InventoryRemoveView, InventoryRestockView

urlpatterns = [
    path("restock/",InventoryRestockView.as_view(),name="inventory-restock",),
    path("remove/",InventoryRemoveView.as_view(),name="inventory-remove",),
]
