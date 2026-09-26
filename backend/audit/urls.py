from django.urls import path

from .views import (
    AuditLogListView,
    AuditObjectLogListView,
)

urlpatterns = [
    path(
        "",
        AuditLogListView.as_view(),
        name="audit-list",
    ),
    path(
        "object/<str:model_name>/<str:object_id>/",
        AuditObjectLogListView.as_view(),
        name="audit-object-list",
    ),
]
