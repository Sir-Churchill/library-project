from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from books.models import Book

from rest_framework.test import APIClient

User = get_user_model()


class BookViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="user", password="pass")
        self.staff_user = User.objects.create_user(
            email="staff@emai.com", password="pass", is_staff=True
        )

        self.book1 = Book.objects.create(
            title="Book1", author="Author1", cover="SOFT", inventory=5, daily_fee=1.5
        )
        self.book2 = Book.objects.create(
            title="Book2", author="Author2", cover="HARD", inventory=3, daily_fee=2.0
        )

    def test_book_list_public(self):
        url = reverse("books:book-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 2)

        self.assertNotIn("inventory", data[0])
        self.assertNotIn("daily_fee", data[0])

    def test_book_retrieve_authenticated(self):
        url = reverse("books:book-detail", args=[self.book1.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("inventory", data)
        self.assertIn("daily_fee", data)

        self.client.force_authenticate(self.user)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("inventory", data)
        self.assertIn("daily_fee", data)

    def test_book_create_permission(self):
        url = reverse("books:book-list")
        data = {
            "title": "BookNew",
            "author": "AuthorNew",
            "cover": "SOFT",
            "inventory": 3,
            "daily_fee": 1.5,
        }

        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 401)

        self.client.force_authenticate(user=self.user)
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 403)

        self.client.force_authenticate(self.staff_user)
        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(Book.objects.filter(title="BookNew").exists())

    def test_book_update_permission(self):
        url = reverse("books:book-detail", args=[self.book1.id])
        data = {"title": "UpdatedTitle"}

        self.client.force_authenticate(user=self.user)
        resp = self.client.patch(url, data)
        self.assertEqual(resp.status_code, 403)

        self.client.force_authenticate(user=self.staff_user)
        resp = self.client.patch(url, data)
        self.assertEqual(resp.status_code, 200)
