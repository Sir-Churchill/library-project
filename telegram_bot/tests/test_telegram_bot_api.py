from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from telegram_bot.models import TelegramToken
from django.urls import reverse

User = get_user_model()


class UpdateUserTelegramAPITest(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="user@test.com", password="pass123")
        self.token = TelegramToken.objects.create(token="tok123", telegram_id=1111)
        self.url = reverse("users:telegram")

    def test_successful_token_update(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.put(self.url, {"token": "tok123"}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["success"], "User updated")

        self.token.refresh_from_db()
        self.assertEqual(self.token.user, self.user)
        self.assertTrue(self.token.is_used)

    def test_token_already_used(self):
        self.token.is_used = True
        self.token.save()
        self.client.force_authenticate(user=self.user)
        resp = self.client.put(self.url, {"token": "tok123"}, format="json")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.data["error"], "Invalid Token")

    def test_invalid_token(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.put(self.url, {"token": "wrongtoken"}, format="json")
        self.assertEqual(resp.status_code, 404)
        self.assertEqual(resp.data["error"], "Invalid Token")

    def test_unauthenticated_user(self):
        resp = self.client.put(self.url, {"token": "tok123"}, format="json")
        self.assertEqual(resp.status_code, 401)
