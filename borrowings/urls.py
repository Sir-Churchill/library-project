from django.urls import path, include
from rest_framework.routers import DefaultRouter

from borrowings.views import BorrowingView, return_book

app_name = "borrowings"

router = DefaultRouter()
router.register("borrowings", BorrowingView)

urlpatterns = [
    path("", include(router.urls)),
    path("borrowings/<int:pk>/return/", return_book, name="return-book"),
]
