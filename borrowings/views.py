from datetime import date

from django.db import transaction
from rest_framework import status, mixins, viewsets
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from books.models import Book
from borrowings.models import Borrowing
from borrowings.serializers import (
    BorrowingSerializer,
    BorrowingListSerializer,
    BorrowingDetailSerializer,
)
from payment.models import Payment
from payment.services import create_payment_session

FINE_MULTIPLE = 2


class BorrowingView(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
):
    queryset = Borrowing.objects.all().prefetch_related("books")
    serializer_class = BorrowingSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return BorrowingListSerializer
        elif self.action == "retrieve":
            return BorrowingDetailSerializer
        return BorrowingSerializer

    @staticmethod
    def _params_to_ints(qs):
        return [int(str_id) for str_id in qs.split(",")]

    def get_queryset(self):
        queryset = self.queryset

        user_id = self.request.query_params.get("user_id")
        is_active = self.request.query_params.get("is_active")

        if self.request.user.is_staff:
            if user_id:
                user_ids = self._params_to_ints(user_id)
                queryset = queryset.filter(user__in=user_ids)

            if is_active:
                if is_active.lower() == "true":
                    queryset = queryset.filter(actual_return_date__isnull=True)
                elif is_active.lower() == "false":
                    queryset = queryset.filter(actual_return_date__isnull=False)

            return queryset

        return queryset.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        serializer = BorrowingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        book_id = request.data.get("book")
        book = Book.objects.select_for_update().get(id=book_id)

        with transaction.atomic():
            if Borrowing.objects.filter(
                user=request.user, book=book, actual_return_date__isnull=True
            ).exists():
                raise ValidationError(f"You already borrowed {book.title}")
            if book.inventory <= 0:
                raise ValidationError(f"{book.title} is out of stock")

            borrowing_instance = serializer.save(user=request.user, book=book)

            book.inventory -= 1
            book.save()

            payment_url = create_payment_session(borrowing_instance)

        response_data = BorrowingSerializer(borrowing_instance).data
        response_data["payment_url"] = payment_url

        return Response(response_data, status=status.HTTP_201_CREATED)


def calculate_fine(borrowing):
    if borrowing.actual_return_date is None:
        return 0

    if borrowing.actual_return_date > borrowing.expected_return:
        days_overdue = (borrowing.actual_return_date - borrowing.expected_return).days
        fine_amount = days_overdue * borrowing.book.daily_fee * FINE_MULTIPLE
        return fine_amount
    return 0


@api_view(["POST"])
def return_book(request, pk):
    borrowing = Borrowing.objects.select_for_update().get(pk=pk)
    book = borrowing.book

    if borrowing.actual_return_date is not None:
        return Response(
            {"detail": "This book was returned"}, status=status.HTTP_400_BAD_REQUEST
        )

    with transaction.atomic():
        book.inventory += 1
        book.save()

        borrowing.actual_return_date = date.today()
        borrowing.save()

        fine_amount = calculate_fine(borrowing)
        fine_payment_url = None
        if fine_amount > 0:
            fine_payment = Payment.objects.create(
                borrowing=borrowing,
                type=Payment.Type.FINE,
                status=Payment.PaymentStatus.PENDING,
                money_to_pay=fine_amount,
            )
            fine_payment_url = create_payment_session(fine_payment)

        serializer = BorrowingSerializer(borrowing)
        data = serializer.data
        if fine_payment_url:
            data["fine_payment_url"] = fine_payment_url

    return Response(data, status=status.HTTP_200_OK)
