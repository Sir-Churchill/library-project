from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from telegram_bot.views import UpdateUserTelegramView
from users.views import CreateUserView, ManageUserView

app_name = "users"

urlpatterns = [
    path("register/", CreateUserView.as_view(), name="register"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("me/", ManageUserView.as_view(), name="me"),
    path("telegram/", UpdateUserTelegramView.as_view(), name="telegram"),
]
