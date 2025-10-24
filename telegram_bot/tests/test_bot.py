from borrowings.models import Borrowing
from books.models import Book
from telegram_bot.bot import check_borrowings, notified_borrowings
from telegram_bot.bot import get_borrowed_books
import datetime
from unittest.mock import patch
from telegram_bot.bot import start, buttons
from django.test import TestCase
from django.contrib.auth import get_user_model
from telegram_bot.models import TelegramToken

User = get_user_model()


class GetBorrowedBooksTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@test.com", password="pass")
        self.book1 = Book.objects.create(
            title="Book1", author="A", cover="HARD", inventory=1, daily_fee=1
        )
        self.book2 = Book.objects.create(
            title="Book2", author="B", cover="SOFT", inventory=1, daily_fee=1
        )
        self.borrowing1 = Borrowing.objects.create(
            user=self.user,
            book=self.book1,
            borrow_date=datetime.date.today(),
            expected_return=datetime.date.today() + datetime.timedelta(days=3),
        )
        self.borrowing2 = Borrowing.objects.create(
            user=self.user,
            book=self.book2,
            borrow_date=datetime.date.today(),
            expected_return=datetime.date.today() + datetime.timedelta(days=5),
        )
        self.token = TelegramToken.objects.create(
            user=self.user, telegram_id=1111, token="tok123"
        )

    def test_returns_all_borrowed_books(self):
        books = get_borrowed_books(1111)
        self.assertEqual(len(books), 2)
        self.assertIn("Book1", books[0])
        self.assertIn("Book2", books[1])

    def test_returns_empty_list_if_no_borrowings(self):
        self.borrowing1.actual_return_date = datetime.date.today()
        self.borrowing1.save()
        self.borrowing2.actual_return_date = datetime.date.today()
        self.borrowing2.save()
        books = get_borrowed_books(1111)
        self.assertEqual(books, [])

    def test_returns_empty_list_if_no_token(self):
        books = get_borrowed_books(9999)
        self.assertEqual(books, [])


class CheckBorrowingsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@test.com", password="pass")
        self.book = Book.objects.create(
            title="Book", author="A", cover="HARD", inventory=1, daily_fee=1
        )
        self.borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            borrow_date=datetime.date.today(),
            expected_return=datetime.date.today() + datetime.timedelta(days=3),
        )
        self.token = TelegramToken.objects.create(
            user=self.user, telegram_id=1111, token="tok123"
        )

    @patch("telegram_bot.bot.bot.send_message")
    def test_send_notification_if_token_exists(self, mock_send):
        notified_borrowings.clear()
        check_borrowings()
        self.assertTrue(mock_send.called)
        self.assertIn(self.borrowing.id, notified_borrowings)

    @patch("telegram_bot.bot.bot.send_message")
    def test_no_notification_if_no_token(self, mock_send):
        self.token.delete()
        notified_borrowings.clear()
        check_borrowings()
        self.assertFalse(mock_send.called)


class BotHandlersTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="user@test.com", password="pass")
        self.token = TelegramToken.objects.create(
            user=self.user, telegram_id=1111, token="tok123"
        )

    @patch("telegram_bot.bot.bot.send_message")
    def test_start_creates_token_if_new_user(self, mock_send):
        telegram_id = 2222
        msg = type(
            "Msg",
            (),
            {
                "from_user": type("User", (), {"id": telegram_id})(),
                "chat": type("Chat", (), {"id": telegram_id})(),
            },
        )()
        start(msg)
        token = TelegramToken.objects.get(telegram_id=telegram_id)
        self.assertFalse(token.is_used)
        self.assertTrue(mock_send.called)

    @patch("telegram_bot.bot.bot.send_message")
    def test_buttons_my_borrowings(self, mock_send):
        msg = type(
            "Msg",
            (),
            {
                "text": "My Borrowings📚",
                "from_user": type("User", (), {"id": self.token.telegram_id})(),
                "chat": type("Chat", (), {"id": self.token.telegram_id})(),
            },
        )()
        buttons(msg)
        self.assertTrue(mock_send.called)

    @patch("telegram_bot.bot.bot.send_message")
    def test_buttons_unknown_text(self, mock_send):
        msg = type(
            "Msg",
            (),
            {
                "text": "Hello",
                "from_user": type("User", (), {"id": self.token.telegram_id})(),
                "chat": type("Chat", (), {"id": self.token.telegram_id})(),
            },
        )()
        buttons(msg)
        self.assertTrue(mock_send.called)
