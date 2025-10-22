from datetime import date
from rest_framework import serializers

from books.models import Book
from books.serializers import BookListSerializer, BookDetailSerializer
from borrowings.models import Borrowing
from payment.serializers import PaymentListSerializer


class BorrowingSerializer(serializers.ModelSerializer):

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return",
            "actual_return_date",
            "book",
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
    book = BookListSerializer(read_only=True)

    class Meta:
        model = Borrowing
        fields = ("id", "borrow_date", "expected_return", "actual_return_date", "book")


class BorrowingDetailSerializer(serializers.ModelSerializer):
    book = BookDetailSerializer(read_only=True)
    payment = PaymentListSerializer(read_only=True, many=True)

    class Meta:
        model = Borrowing
        fields = (
            "id",
            "borrow_date",
            "expected_return",
            "actual_return_date",
            "book",
            "payment",
            "user",
        )
