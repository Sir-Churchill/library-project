from django.urls import path, include
from rest_framework import routers

from payment.views import (
    PaymentGenericView,
    PaymentCheckoutView,
    PaymentSuccessView,
    PaymentCanceledView,
)

app_name = "payment"

router = routers.DefaultRouter()
router.register("transactions", PaymentGenericView)
urlpatterns = [
    path("", include(router.urls)),
    path(
        "checkout/<int:borrowing_id>/", PaymentCheckoutView.as_view(), name="checkout"
    ),
    path(
        "success/",
        PaymentSuccessView.as_view(),
        name="success",
    ),
    path(
        "cancel/",
        PaymentCanceledView.as_view(),
        name="cancel",
    ),
]
