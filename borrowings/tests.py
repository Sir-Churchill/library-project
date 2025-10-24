from datetime import date, timedelta
from unittest.mock import patch, MagicMock

from rest_framework.test import APIClient
from django.test import TestCase
from django.urls import reverse
from django.contrib.auth import get_user_model

from books.models import Book
from borrowings.models import Borrowing
from payment.models import Payment

User = get_user_model()


class BorrowingViewSetTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="user@test.com", password="pass")
        self.staff_user = User.objects.create_user(
            email="staff@test.com", password="pass", is_staff=True
        )

        self.book1 = Book.objects.create(
            title="Book1", author="Author1", cover="SOFT", inventory=5, daily_fee=2.00
        )
        self.book2 = Book.objects.create(
            title="Book2", author="Author2", cover="HARD", inventory=3, daily_fee=3.00
        )

        self.borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book1,
            expected_return=date.today() - timedelta(days=1),  # просрочена
        )

    def test_borrowing_create(self):
        url = reverse("borrowings:borrowing-list")
        self.client.force_authenticate(self.user)
        data = {
            "book": self.book2.id,
            "expected_return": str(date.today() + timedelta(days=7)),
        }

        resp = self.client.post(url, data)
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(
            Borrowing.objects.filter(user=self.user, book=self.book2).exists()
        )
        self.book2.refresh_from_db()
        self.assertEqual(self.book2.inventory, 2)

    @patch("payment.services.stripe.checkout.Session.create")
    def test_borrowing_return_and_fine(self, mock_stripe_create):
        # Мокаем сессию Stripe
        mock_session = MagicMock()
        mock_session.id = "sess_test"
        mock_session.url = "https://stripe.test/session"
        mock_stripe_create.return_value = mock_session

        url = reverse("borrowings:return-book", args=[self.borrowing.id])
        self.client.force_authenticate(self.user)

        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200)

        self.borrowing.refresh_from_db()
        self.book1.refresh_from_db()

        self.assertIsNotNone(self.borrowing.actual_return_date)
        self.assertEqual(self.book1.inventory, 6)

        fine_payment = Payment.objects.filter(
            borrowing=self.borrowing, type=Payment.Type.FINE
        ).first()
        self.assertIsNotNone(fine_payment)
        self.assertEqual(fine_payment.money_to_pay, 4.00)

    @patch("payment.services.stripe.checkout.Session.create")
    def test_borrowing_return_twice(self, mock_stripe_create):
        mock_session = MagicMock()
        mock_session.id = "sess_test"
        mock_session.url = "https://stripe.test/session"
        mock_stripe_create.return_value = mock_session

        url = reverse("borrowings:return-book", args=[self.borrowing.id])
        self.client.force_authenticate(self.user)

        resp1 = self.client.post(url)
        self.assertEqual(resp1.status_code, 200)

        resp2 = self.client.post(url)
        self.assertEqual(resp2.status_code, 400)
        self.assertIn("This book was returned", resp2.json()["detail"])


def test_borrowing_list_permissions(self):
    url = reverse("borrowings:borrowing-list")

    resp = self.client.get(url)
    self.assertEqual(resp.status_code, 401)

    self.client.force_authenticate(self.user)
    resp = self.client.get(url)
    self.assertEqual(resp.status_code, 200)
    data = resp.json()
    for item in data:
        self.assertEqual(item["book"]["id"], self.book1.id)

    self.client.force_authenticate(self.staff_user)
    resp = self.client.get(url)
    self.assertEqual(resp.status_code, 200)
    data = resp.json()
    self.assertTrue(len(data) >= 1)
