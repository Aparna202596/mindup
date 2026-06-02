from django.db import models
from apps.core.models import TimeStampedModel
from apps.users.models import CustomUser
from apps.categories.models import SubCategory
from django.contrib.postgres.search import SearchVectorField

class Question(TimeStampedModel):
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, related_name="questions")

    title = models.TextField()

    normalized_title = models.TextField(blank=True, null=True)

    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    view_count = models.PositiveIntegerField(default=0)

    search_vector = SearchVectorField(null=True)

    class Meta:
        indexes = [
            models.Index(fields=["normalized_title"]),
        ]

    def __str__(self):
        return self.title
