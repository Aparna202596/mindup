from django.db import models
from apps.core.models import TimeStampedModel
from apps.users.models import CustomUser


class ApprovalQueue(TimeStampedModel):

    OBJECT_TYPES = [
        ("topic", "Topic"),
        ("category", "Category"),
        ("subcategory", "SubCategory"),
    ]

    object_type = models.CharField(max_length=50, choices=OBJECT_TYPES)

    object_id = models.UUIDField()

    requested_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

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

    reviewed_by = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviews"
    )