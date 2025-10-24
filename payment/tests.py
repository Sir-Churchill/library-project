import datetime
from unittest.mock import patch, MagicMock

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model

from books.models import Book
from borrowings.models import Borrowing
from payment.models import Payment

User = get_user_model()


class PaymentViewSetTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            email="user@example.com", password="pass123"
        )
        self.admin = User.objects.create_superuser(
            email="admin@example.com", password="adminpass"
        )
        self.book = Book.objects.create(
            title="Django for APIs",
            author="William S. Vincent",
            cover="HARD",
            inventory=3,
            daily_fee=2.50,
        )
        self.borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            borrow_date=datetime.date.today(),
            expected_return=datetime.date.today() + datetime.timedelta(days=3),
        )
        self.payment = Payment.objects.create(
            status=Payment.PaymentStatus.PENDING,
            type=Payment.Type.PAYMENT,
            borrowing=self.borrowing,
            session_url="https://example.com/session",
            session_id="sess_123",
            money_to_pay=5.00,
        )

    def test_user_can_only_see_own_payments(self):
        url = reverse("payment:transactions-list")
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["id"], self.payment.id)

    def test_admin_can_see_all_payments(self):
        url = reverse("payment:transactions-list")
        self.client.force_authenticate(user=self.admin)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)

    def test_anonymous_gets_empty_list(self):
        url = reverse("payment:transactions-list")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 401)

    def test_retrieve_payment_detail(self):
        url = reverse("payment:transactions-detail", args=[self.payment.id])
        self.client.force_authenticate(user=self.user)
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["id"], self.payment.id)
        self.assertEqual(resp.data["money_to_pay"], "5.00")


class PaymentCheckoutViewTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@test.com", password="pass123")
        self.book = Book.objects.create(
            title="Test Book",
            author="Tester",
            cover="HARD",
            inventory=2,
            daily_fee=1.5,
        )
        self.borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            borrow_date=datetime.date.today(),
            expected_return=datetime.date.today() + datetime.timedelta(days=3),
        )

    @patch("stripe.checkout.Session.create")
    def test_checkout_creates_payment(self, mock_stripe):
        mock_session = MagicMock()
        mock_session.id = "sess_abc"
        mock_session.url = "https://stripe.test/session"
        mock_stripe.return_value = mock_session

        self.client.force_authenticate(user=self.user)
        url = reverse("payment:checkout", kwargs={"borrowing_id": self.borrowing.id})

        resp = self.client.post(url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["session_id"], "sess_abc")
        self.assertEqual(resp.data["url"], "https://stripe.test/session")

        payment = Payment.objects.get(borrowing=self.borrowing)
        self.assertEqual(payment.status, Payment.PaymentStatus.PENDING)
        self.assertEqual(payment.type, Payment.Type.PAYMENT)
        self.assertAlmostEqual(float(payment.money_to_pay), 1.5 * 3, places=2)

    def test_checkout_nonexistent_borrowing_returns_404(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("payment:checkout", kwargs={"borrowing_id": 999})
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 404)


class PaymentResultViewsTestCase(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="u@test.com", password="pass")

    @patch("stripe.checkout.Session.retrieve")
    def test_success_view_updates_payment(self, mock_retrieve):
        book = Book.objects.create(
            title="Book", author="A", cover="HARD", inventory=2, daily_fee=2
        )
        borrowing = Borrowing.objects.create(
            user=self.user,
            book=book,
            borrow_date=datetime.date(2025, 1, 1),
            expected_return=datetime.date(2025, 1, 3),
        )
        payment = Payment.objects.create(
            status=Payment.PaymentStatus.PENDING,
            type=Payment.Type.PAYMENT,
            borrowing=borrowing,
            session_url="url",
            session_id="sess_1",
            money_to_pay=6.0,
        )

        mock_retrieve.return_value = MagicMock(
            metadata={"borrowing_id": borrowing.id, "user_id": self.user.id}
        )

        self.client.force_authenticate(user=self.user)
        url = reverse("payment:success") + "?session_id=sess_1"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)

        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.PaymentStatus.PAID)
        self.assertEqual(str(resp.data["borrowing_id"]), str(borrowing.id))

    def test_success_view_no_session_id(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("payment:success")
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 400)

    def test_canceled_view_returns_canceled(self):
        self.client.force_authenticate(user=self.user)
        url = reverse("payment:cancel") + "?session_id=sess_x"
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("Canceled", resp.data["detail"])
