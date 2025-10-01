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


class BorrowingView(
    viewsets.GenericViewSet,
    mixins.RetrieveModelMixin,
    mixins.ListModelMixin,
    mixins.CreateModelMixin,
):
    queryset = Borrowing.objects.all()
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
                queryset = queryset.filter(user_id__in=user_ids)

            if is_active:
                if is_active.lower() == "true":
                    queryset = queryset.filter(actual_return_date__isnull=True)
                elif is_active.lower() == "false":
                    queryset = queryset.filter(actual_return_date__isnull=False)

            return queryset

        return queryset.filter(user_id=self.request.user.id)

    def create(self, request, *args, **kwargs):
        serializer = BorrowingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        book_id = serializer.validated_data["book_id"]
        book = Book.objects.select_for_update().get(pk=book_id)
        with transaction.atomic():
            if book.inventory <= 0:
                raise ValidationError("This book is out of stock")

            book.inventory -= 1
            book.save()

            if Borrowing.objects.filter(
                user_id=request.user.id,
                book_id=book_id,
                actual_return_date__isnull=True,
            ).exists():
                raise ValidationError(
                    "You already borrowed this book and haven't returned it yet."
                )
            else:
                serializer.save(user_id=request.user.id)

        return Response(serializer.data, status=status.HTTP_200_OK)

    def perform_create(self, serializer):
        user = self.request.user
        serializer.save(user_id=user.id)


@api_view(["POST"])
def return_book(request, pk):
    borrowing = Borrowing.objects.select_for_update().get(pk=pk)
    book = Book.objects.select_for_update().get(id=borrowing.book_id)

    if borrowing.actual_return_date is None:

        with transaction.atomic():
            book.inventory += 1
            book.save()
            borrowing.actual_return_date = date.today()
            borrowing.save()

            serializer = BorrowingSerializer(borrowing)
        return Response(serializer.data, status=status.HTTP_200_OK)
    else:
        return Response(
            {"detail": "This book was returned"}, status=status.HTTP_400_BAD_REQUEST
        )
