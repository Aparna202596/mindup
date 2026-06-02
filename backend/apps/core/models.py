import uuid
from django.db import models

class TimeStampedModel(models.Model):

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

from django.db import models
from apps.core.models import TimeStampedModel
from apps.users.models import CustomUser


class AuditLog(TimeStampedModel):

    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)

    action = models.CharField(max_length=255)

    object_type = models.CharField(max_length=255)

    object_id = models.UUIDField()

    previous_data = models.JSONField(null=True, blank=True)

    new_data = models.JSONField(null=True, blank=True)