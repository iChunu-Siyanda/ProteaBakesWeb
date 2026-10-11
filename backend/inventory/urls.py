from django.urls import path

from .views import InventoryListView, InventoryRemoveView, InventoryRestockView

urlpatterns = [
    path("", InventoryListView.as_view(), name="inventory-list"),
    path("restock/",InventoryRestockView.as_view(),name="inventory-restock",),
    path("remove/",InventoryRemoveView.as_view(),name="inventory-remove",),
]
