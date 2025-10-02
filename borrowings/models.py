from django.db import models

from books.models import Book
from library_project import settings


class Borrowing(models.Model):
    borrow_date = models.DateField(auto_now_add=True)
    expected_return = models.DateField()
    actual_return_date = models.DateField(blank=True, null=True)
    book = models.ManyToManyField(Book)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.borrow_date} - {self.expected_return}"

    class Meta:
        ordering = ["borrow_date"]
