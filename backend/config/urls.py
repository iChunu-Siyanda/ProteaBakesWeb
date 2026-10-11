"""URL configuration for the Protea Bakes API."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


class ThrottledTokenObtainPairView(TokenObtainPairView):
    throttle_scope = "auth"


class ThrottledTokenRefreshView(TokenRefreshView):
    throttle_scope = "auth"


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("catalog.urls")),

    path("api/auth/", include("users.urls")),
    path("api/auth/token/", ThrottledTokenObtainPairView.as_view(), name="token-obtain"),
    path("api/auth/token/refresh/", ThrottledTokenRefreshView.as_view(), name="token-refresh"),

    path("api/cart/", include("cart.urls")),
    path("api/orders/", include("orders.urls")),
    path("api/payments/", include("payments.urls")),
    path("api/fulfillment/", include("fulfillment.urls")),
    path("api/inventory/", include("inventory.urls")),
    path("api/promotions/", include("promotions.urls")),
    path("api/reviews/", include("reviews.urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/audit/", include("audit.urls")),

    # API documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

if settings.DEBUG:
    # In production, serve /media/ from object storage or the web server.
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
