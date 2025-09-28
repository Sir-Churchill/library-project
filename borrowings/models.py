from django.db import models


class Borrowing(models.Model):
    borrow_date = models.DateField(auto_now_add=True)
    expected_return = models.DateField()
    actual_return_date = models.DateField()
    book_id = models.IntegerField()
    user_id = models.IntegerField()

    def __str__(self):
        return f"{self.borrow_date} - {self.expected_return}"
