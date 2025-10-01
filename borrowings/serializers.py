from datetime import date
from rest_framework import serializers

from books.models import Book
from borrowings.models import Borrowing


class BorrowingSerializer(serializers.ModelSerializer):

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return",
            "actual_return_date",
            "book_id",
        )

    def validate(self, data):
        borrow_date = getattr(self.instance, "borrow_date", None) or date.today()
        expected_return = data.get("expected_return") or getattr(
            self.instance, "expected_return", None
        )

        if expected_return < borrow_date:
            raise serializers.ValidationError(
                {
                    "expected_return": "Expected return date cannot be earlier than borrow date."
                }
            )

        book_id = data.get("book_id") or getattr(self.instance, "book_id", None)
        if book_id and not Book.objects.filter(pk=book_id).exists():
            raise serializers.ValidationError({"book_id": "Book does not exist."})

        return data


class BorrowingListSerializer(serializers.ModelSerializer):
    book = serializers.SerializerMethodField()

    class Meta:
        model = Borrowing
        fields = ("id", "borrow_date", "expected_return", "actual_return_date", "book")

    def get_book(self, obj):
        book = Book.objects.get(pk=obj.book_id)
        return {
            "id": book.id,
            "title": book.title,
        }


class BorrowingDetailSerializer(serializers.ModelSerializer):
    book = serializers.SerializerMethodField()

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return",
            "actual_return_date",
            "book",
            "user_id",
        )

    def get_book(self, obj):
        book = Book.objects.get(pk=obj.book_id)
        return {
            "id": book.id,
            "title": book.title,
            "author": book.author,
            "cover": book.cover,
            "daily_fee": book.daily_fee,
        }
