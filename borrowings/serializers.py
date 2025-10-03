from datetime import date
from rest_framework import serializers

from books.models import Book
from books.serializers import BookListSerializer, BookDetailSerializer
from borrowings.models import Borrowing


class BorrowingSerializer(serializers.ModelSerializer):
    books = serializers.PrimaryKeyRelatedField(many=True, queryset=Book.objects.all())

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return",
            "actual_return_date",
            "books",
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

        return data


class BorrowingListSerializer(serializers.ModelSerializer):
    books = BookListSerializer(read_only=True, many=True)

    class Meta:
        model = Borrowing
        fields = ("id", "borrow_date", "expected_return", "actual_return_date", "books")


class BorrowingDetailSerializer(serializers.ModelSerializer):
    books = BookDetailSerializer(read_only=True, many=True)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return",
            "actual_return_date",
            "books",
            "user",
        )
