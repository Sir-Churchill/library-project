from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("api/v1/", include("books.urls", namespace="books")),
    path("api/v2/", include("borrowings.urls", namespace="borrowings")),
    path("api/users/", include("users.urls", namespace="users")),
    path("admin/", admin.site.urls),
]
