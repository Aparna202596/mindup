from django.db import models
from apps.core.models import TimeStampedModel
from apps.users.models import CustomUser


class Topic(TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)

    description = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    class Meta:
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name
