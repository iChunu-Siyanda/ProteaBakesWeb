from django.urls import path
from .views import PromotionRedeemView, PromotionValidateView

urlpatterns = [
    path("validate/",PromotionValidateView.as_view(),name="promotion-validate",),
    path("redeem/",PromotionRedeemView.as_view(),name="promotion-redeem",),
]
