from django.urls import path

from .views import PaymentInitiateView, PaymentWebhookView, YocoWebhookView

urlpatterns = [
    path("initiate/", PaymentInitiateView.as_view(), name="payment-initiate"),
    path("webhook/", PaymentWebhookView.as_view(), name="payment-webhook"),
    path("webhook/yoco/", YocoWebhookView.as_view(), name="payment-webhook-yoco"),
]
