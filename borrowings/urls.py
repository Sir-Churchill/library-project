from django.urls import path, include
from rest_framework.routers import DefaultRouter

from borrowings.views import BorrowingView

app_name = "borrowings"

router = DefaultRouter()
router.register("borrowings", BorrowingView)

urlpatterns = [
    path("", include(router.urls)),
]
