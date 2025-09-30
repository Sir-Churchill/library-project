from django.db import models
from rest_framework.exceptions import ValidationError

from books.models import Book


class Borrowing(models.Model):
    borrow_date = models.DateField(auto_now_add=True)
    expected_return = models.DateField()
    actual_return_date = models.DateField(blank=True, null=True)
    book_id = models.IntegerField()
    user_id = models.IntegerField()

    def __str__(self):
        return f"{self.borrow_date} - {self.expected_return}"

    class Meta:
        ordering = ["borrow_date"]

    def clean(self):
        if self.expected_return < self.borrow_date:
            raise ValidationError(
                "Expected return date cannot be earlier than borrow date"
            )
        if self.book_id:
            try:
                book = Book.objects.get(pk=self.book_id)
            except Book.DoesNotExist:
                raise ValidationError("Book does not exist")

    def save(self, *args, **kwargs):
        self.full_clean()

        return super(Borrowing, self).save(*args, **kwargs)
