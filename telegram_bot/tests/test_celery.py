from unittest.mock import patch


from django.test import TestCase
from django.contrib.auth import get_user_model

from books.models import Book
from borrowings.models import Borrowing
from telegram_bot.models import TelegramToken
from telegram_bot import tasks
from telegram_bot.bot import get_borrowed_books

User = get_user_model()


class TelegramBotHelpersTestCase(TestCase):
    """Test the helper functions from telegram_bot.bot"""

    def setUp(self):
        self.user = User.objects.create_user(email="user@test.com", password="pass")
        self.book = Book.objects.create(
            title="Test Book",
            author="Test Author",
            cover="HARD",
            inventory=5,
            daily_fee=2.0,
        )
        self.telegram_token = TelegramToken.objects.create(
            user=self.user, telegram_id=12345, token="tok123"
        )

    def test_get_borrowed_books_returns_books(self):
        """Test get_borrowed_books returns formatted book list"""
        from datetime import date as real_date

        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return=real_date(2025, 10, 30),
            actual_return_date=None,
        )
        Borrowing.objects.filter(pk=borrowing.pk).update(
            borrow_date=real_date(2025, 10, 15)
        )

        result = get_borrowed_books(12345)

        self.assertEqual(len(result), 1)
        self.assertIn("Test Book", result[0])
        self.assertIn("Test Author", result[0])

    def test_get_borrowed_books_no_token(self):
        """Test get_borrowed_books with non-existent token"""
        result = get_borrowed_books(99999)
        self.assertEqual(result, [])

    def test_get_borrowed_books_ignores_returned(self):
        """Test get_borrowed_books ignores returned books"""
        from datetime import date as real_date

        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return=real_date(2025, 10, 22),
            actual_return_date=real_date(2025, 10, 21),
        )
        Borrowing.objects.filter(pk=borrowing.pk).update(
            borrow_date=real_date(2025, 10, 15)
        )

        result = get_borrowed_books(12345)
        self.assertEqual(len(result), 0)


class TelegramCeleryTasksTestCase(TestCase):
    """Test the Celery tasks"""

    def setUp(self):
        self.user = User.objects.create_user(email="user@test.com", password="pass")
        self.book = Book.objects.create(
            title="Test Book", author="Author", cover="HARD", inventory=5, daily_fee=2.0
        )
        self.telegram_token = TelegramToken.objects.create(
            user=self.user, telegram_id=12345, token="tok123"
        )

    @patch("telegram_bot.tasks.get_borrowed_books")
    @patch("telegram_bot.tasks.bot")
    @patch("telegram_bot.tasks.date")
    def test_send_reminder_sends_message(
        self, mock_date_class, mock_bot, mock_get_borrowed_books
    ):
        """Test send_reminder with mocked date"""
        from datetime import date as real_date

        mock_date_class.today.return_value = real_date(2025, 10, 24)
        mock_date_class.side_effect = lambda *args, **kw: real_date(*args, **kw)

        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return=real_date(2025, 10, 30),
            actual_return_date=None,
        )

        Borrowing.objects.filter(pk=borrowing.pk).update(
            borrow_date=real_date(2025, 10, 15)
        )

        mock_get_borrowed_books.return_value = ["Test Book by Author"]

        tasks.send_reminder()

        mock_get_borrowed_books.assert_called_once_with(12345)
        mock_bot.send_message.assert_called_once()

        call_kwargs = mock_bot.send_message.call_args[1]
        self.assertEqual(call_kwargs["chat_id"], 12345)
        self.assertIn("reminder", call_kwargs["text"].lower())

    @patch("telegram_bot.tasks.get_borrowed_books")
    @patch("telegram_bot.tasks.bot")
    @patch("telegram_bot.tasks.date")
    def test_send_due_today_sends_message(
        self, mock_date_class, mock_bot, mock_get_borrowed_books
    ):
        """Test send_due_today with mocked date"""
        from datetime import date as real_date

        mock_date_class.today.return_value = real_date(2025, 10, 24)
        mock_date_class.side_effect = lambda *args, **kw: real_date(*args, **kw)

        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return=real_date(2025, 10, 24),  # Due today
            actual_return_date=None,
        )
        Borrowing.objects.filter(pk=borrowing.pk).update(
            borrow_date=real_date(2025, 10, 17)
        )

        mock_get_borrowed_books.return_value = ["Test Book by Author"]

        tasks.send_due_today()

        mock_get_borrowed_books.assert_called_once_with(12345)
        mock_bot.send_message.assert_called_once()

        call_kwargs = mock_bot.send_message.call_args[1]
        self.assertEqual(call_kwargs["chat_id"], 12345)
        self.assertIn("Today is the day to return books", call_kwargs["text"])

    @patch("telegram_bot.tasks.bot")
    @patch("telegram_bot.tasks.date")
    def test_send_reminder_no_token(self, mock_date_class, mock_bot):
        """Test send_reminder when user has no telegram token"""
        from datetime import date as real_date

        mock_date_class.today.return_value = real_date(2025, 10, 24)
        mock_date_class.side_effect = lambda *args, **kw: real_date(*args, **kw)

        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return=real_date(2025, 10, 30),
            actual_return_date=None,
        )
        Borrowing.objects.filter(pk=borrowing.pk).update(
            borrow_date=real_date(2025, 10, 15)
        )

        self.telegram_token.delete()

        tasks.send_reminder()

        mock_bot.send_message.assert_not_called()

    @patch("telegram_bot.tasks.get_borrowed_books")
    @patch("telegram_bot.tasks.bot")
    @patch("telegram_bot.tasks.date")
    def test_send_reminder_no_borrowed_books(
        self, mock_date_class, mock_bot, mock_get_borrowed_books
    ):
        """Test send_reminder when get_borrowed_books returns empty"""
        from datetime import date as real_date

        mock_date_class.today.return_value = real_date(2025, 10, 24)
        mock_date_class.side_effect = lambda *args, **kw: real_date(*args, **kw)

        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return=real_date(2025, 10, 30),
            actual_return_date=None,
        )
        Borrowing.objects.filter(pk=borrowing.pk).update(
            borrow_date=real_date(2025, 10, 15)
        )

        mock_get_borrowed_books.return_value = []

        tasks.send_reminder()

        mock_get_borrowed_books.assert_called_once_with(12345)
        mock_bot.send_message.assert_not_called()

    @patch("telegram_bot.tasks.bot")
    @patch("telegram_bot.tasks.date")
    def test_send_reminder_ignores_recent_borrowings(self, mock_date_class, mock_bot):
        """Test that recent borrowings (< 3 days) don't trigger reminder"""
        from datetime import date as real_date

        mock_date_class.today.return_value = real_date(2025, 10, 24)
        mock_date_class.side_effect = lambda *args, **kw: real_date(*args, **kw)

        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return=real_date(2025, 10, 30),
            actual_return_date=None,
        )
        Borrowing.objects.filter(pk=borrowing.pk).update(
            borrow_date=real_date(2025, 10, 23)
        )

        tasks.send_reminder()

        mock_bot.send_message.assert_not_called()

    @patch("telegram_bot.tasks.bot")
    @patch("telegram_bot.tasks.date")
    def test_send_reminder_ignores_returned_books(self, mock_date_class, mock_bot):
        """Test that returned books don't trigger reminder"""
        from datetime import date as real_date

        mock_date_class.today.return_value = real_date(2025, 10, 24)
        mock_date_class.side_effect = lambda *args, **kw: real_date(*args, **kw)

        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return=real_date(2025, 10, 22),
            actual_return_date=real_date(2025, 10, 21),  # Already returned
        )
        Borrowing.objects.filter(pk=borrowing.pk).update(
            borrow_date=real_date(2025, 10, 15)
        )

        tasks.send_reminder()

        mock_bot.send_message.assert_not_called()

    @patch("telegram_bot.tasks.bot")
    @patch("telegram_bot.tasks.date")
    def test_send_due_today_ignores_other_dates(self, mock_date_class, mock_bot):
        """Test that send_due_today only sends for books due today"""
        from datetime import date as real_date

        mock_date_class.today.return_value = real_date(2025, 10, 24)
        mock_date_class.side_effect = lambda *args, **kw: real_date(*args, **kw)

        borrowing = Borrowing.objects.create(
            user=self.user,
            book=self.book,
            expected_return=real_date(2025, 10, 25),  # Due tomorrow
            actual_return_date=None,
        )
        Borrowing.objects.filter(pk=borrowing.pk).update(
            borrow_date=real_date(2025, 10, 17)
        )

        tasks.send_due_today()

        mock_bot.send_message.assert_not_called()
