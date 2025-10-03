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
        book_ids = request.data.get("books")
        books = Book.objects.select_for_update().filter(id__in=book_ids)

        with transaction.atomic():

            for book in books:
                if Borrowing.objects.filter(
                    user=request.user, books=book, actual_return_date__isnull=True
                ).exists():
                    raise ValidationError(f"You already borrowed {book.title}")
                if book.inventory <= 0:
                    raise ValidationError(f"{book.title} is out of stock")

            borrowing_instance = serializer.save(user=request.user)
            borrowing_instance.books.set(books)

            for book in books:
                book.inventory -= 1
                book.save()

        return Response(
            BorrowingSerializer(borrowing_instance).data, status=status.HTTP_201_CREATED
        )


@api_view(["POST"])
def return_book(request, pk):
    borrowing = Borrowing.objects.select_for_update().get(pk=pk)
    books = Book.objects.select_for_update()

    if borrowing.actual_return_date is None:

        with transaction.atomic():
            for book in books:
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
