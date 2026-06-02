from django.db import models
from apps.core.models import TimeStampedModel
from apps.users.models import CustomUser
from apps.topics.models import Topic


class Category(TimeStampedModel):
    topic = models.ForeignKey(Topic, on_delete=models.CASCADE, related_name="categories")

    name = models.CharField(max_length=255)

    description = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    is_approved = models.BooleanField(default=False)

    class Meta:
        unique_together = ("topic", "name")
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return self.name

class SubCategory(TimeStampedModel):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")

    name = models.CharField(max_length=255)

    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    is_approved = models.BooleanField(default=False)

    class Meta:
        unique_together = ("category", "name")

    def __str__(self):
        return self.name