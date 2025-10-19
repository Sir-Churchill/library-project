from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.authentication import JWTAuthentication

from telegram_bot.models import TelegramToken
from telegram_bot.serializers import TelegramTokenSerializer


class UpdateUserTelegramView(generics.UpdateAPIView):
    serializer_class = TelegramTokenSerializer
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        token_value = request.data.get("token")
        token = TelegramToken.objects.filter(token=token_value, is_used=False).first()

        if not token:
            return Response(
                {"error": "Invalid Token"}, status=status.HTTP_404_NOT_FOUND
            )

        token.user = request.user
        token.is_used = True
        token.save()

        return Response({"success": "User updated"}, status=status.HTTP_200_OK)
