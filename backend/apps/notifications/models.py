from django.db import models
from apps.core.models import TimeStampedModel
from apps.users.models import CustomUser


class Notification(TimeStampedModel):

    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    title = models.CharField(max_length=255)

    message = models.TextField()

    is_read = models.BooleanField(default=False)
