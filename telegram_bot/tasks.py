from datetime import date, timedelta

from celery import shared_task

from telegram_bot.models import TelegramToken
from borrowings.models import Borrowing
from telegram_bot.bot import bot, get_borrowed_books


@shared_task
def send_reminder():
    three_days_ago = date.today() - timedelta(days=3)
    borrowings = Borrowing.objects.filter(
        actual_return_date__isnull=True, borrow_date__lte=three_days_ago
    ).prefetch_related("books", "user")

    for borrowing in borrowings:
        try:
            token = TelegramToken.objects.get(user=borrowing.user)
            telegram_id = token.telegram_id
        except TelegramToken.DoesNotExist:
            continue

        borrowed_books = get_borrowed_books(telegram_id)
        if borrowed_books:
            message = (
                "📚 Hello, this is a reminder that you have borrowed a book that will arrive every 3 days so that you don't forget to return it. Books you have borrowed:\n"
                + "\n".join(borrowed_books)
            )

            bot.send_message(chat_id=telegram_id, text=message)


@shared_task
def send_due_today():
    today = date.today()
    borrowings = Borrowing.objects.filter(
        actual_return_date__isnull=True, expected_return=today
    ).prefetch_related("books", "user")

    for borrowing in borrowings:
        try:
            token = TelegramToken.objects.get(user=borrowing.user)
            telegram_id = token.telegram_id
        except TelegramToken.DoesNotExist:
            continue

        borrowed_books = get_borrowed_books(telegram_id)
        if borrowed_books:
            message = (
                "⚠️ Today is the day to return books:\n"
                + "\n".join(borrowed_books)
                + "\nIf you don't return it today, you will be charged a penalty."
            )
            bot.send_message(chat_id=telegram_id, text=message)
