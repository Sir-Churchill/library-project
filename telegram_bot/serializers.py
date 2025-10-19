from rest_framework import serializers

from telegram_bot.models import TelegramToken


class TelegramTokenSerializer(serializers.ModelSerializer):
    class Meta:
        model = TelegramToken
        fields = ("id", "token", "is_used", "created_at")
        read_only_fields = ("is_used", "created_at")
