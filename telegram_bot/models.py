from django.db import models

from library_project import settings


class TelegramToken(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, blank=True, null=True
    )
    token = models.CharField(max_length=255)
    telegram_id = models.BigIntegerField()
    is_used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
