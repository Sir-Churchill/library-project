from django.db import models


class Payment(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = "PENDING"
        PAID = "PAID"

    class Type(models.TextChoices):
        PAYMENT = "PAYMENT"
        FINE = "FINE"

    status = models.CharField(choices=PaymentStatus.choices)
    type = models.CharField(choices=Type.choices)
    borrowing = models.ForeignKey("borrowings.Borrowing", on_delete=models.CASCADE)
    session_url = models.URLField()
    session_id = models.CharField(max_length=255)
    money_to_pay = models.DecimalField(decimal_places=2, max_digits=10)

    def __str__(self):
        return f"Status: {self.status} Type: {self.type}"
