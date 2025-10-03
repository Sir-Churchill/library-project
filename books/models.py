from django.db import models


class Book(models.Model):
    class Cover(models.TextChoices):
        SOFT = ("SOFT",)
        HARD = ("HARD",)

    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    cover = models.CharField(choices=Cover.choices)
    inventory = models.PositiveIntegerField()
    daily_fee = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.author} - {self.title}"
