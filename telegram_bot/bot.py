import os
import django
import secrets

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "library_project.settings")
django.setup()

import telebot
from telebot import types
from borrowings.models import Borrowing
from library_project.settings import TELEGRAM_TOKEN
from telegram_bot.models import TelegramToken


bot = telebot.TeleBot(TELEGRAM_TOKEN)


def get_borrowed_books(telegram_id):
    try:
        token = TelegramToken.objects.select_related("user").get(
            telegram_id=telegram_id
        )
        user = token.user
        borrowings = Borrowing.objects.filter(
            user=user, actual_return_date__isnull=True
        ).prefetch_related("books")

        borrowed_books = []
        for borrowing in borrowings:
            for book in borrowing.books.all():
                borrowed_books.append(
                    f"📘 {book.title} — {book.author}\n"
                    f"🗓 Reading period: {borrowing.borrow_date} — {borrowing.expected_return}\n"
                )

        return borrowed_books
    except TelegramToken.DoesNotExist:
        return []


@bot.message_handler(commands=["start"])
def start(message):
    telegram_id = message.from_user.id
    token_auth = secrets.token_urlsafe(16)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard.add("My Borrowings")

    auth = TelegramToken.objects.filter(
        telegram_id=telegram_id, user__isnull=False
    ).exists()

    bot.send_message(
        message.chat.id,
        "Hello! I am BookWormBot — I help you track borrowed books!",
        reply_markup=keyboard,
    )

    if not auth:
        bot.send_message(
            message.chat.id,
            f"You're not authorized yet. Here’s your one-time token: {token_auth}. Use it on our website to link your account.",
        )
        TelegramToken.objects.create(telegram_id=telegram_id, token=token_auth)
    else:
        bot.send_message(
            message.chat.id, "You were already registered, glad to see you again!"
        )


@bot.message_handler(func=lambda message: True)
def buttons(message):
    telegram_id = message.from_user.id
    if message.text == "My Borrowings📚":
        borrowings = get_borrowed_books(telegram_id)
        book_list = (
            "\n".join(borrowings) if borrowings else "You have no borrowed books."
        )
        bot.send_message(message.chat.id, f"📚 Your borrowed books:\n\n{book_list}")
    if message.text == "Visit MyLibrary site":
        bot.send_message(
            message.chat.id, "Here is the link: http://127.0.0.1:8000/api/v1/books/"
        )

    else:
        bot.send_message(
            message.chat.id, "Sorry, I don't understand you. Please choose button."
        )


if __name__ == "__main__":
    print("Starting Telegram Bot...")
    bot.polling()
