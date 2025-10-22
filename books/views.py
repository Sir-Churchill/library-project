from rest_framework import viewsets, permissions

from books.models import Book
from books.permissions import IsAdminOrAuthenticatedOrReadOnly
from books.serializers import BookSerializer, BookListSerializer, BookDetailSerializer


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all()
    serializer_class = BookSerializer

    def get_serializer_class(self):
        if self.action == "list":
            return BookListSerializer
        elif self.action == "retrieve":
            return BookDetailSerializer
        return BookSerializer

    def get_permissions(self):
        if self.action == "list":
            return [permissions.AllowAny()]
        return [IsAdminOrAuthenticatedOrReadOnly()]
