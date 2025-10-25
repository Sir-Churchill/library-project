from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

urlpatterns = [
    path("api/v1/", include("books.urls", namespace="books")),
    path("api/v2/", include("borrowings.urls", namespace="borrowings")),
    path("api/users/", include("users.urls", namespace="users")),
    path("api/payments/", include("payment.urls", namespace="payment")),
    path("api/shema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/schema/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="schema-swagger",
    ),
    path(
        "api/schema/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="schema-redoc",
    ),
    path("admin/", admin.site.urls),
]
