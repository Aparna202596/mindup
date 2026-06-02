from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid


class Role(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class CustomUser(AbstractUser):
    """
    Google OAuth will map into this model.
    No username/password signup flow for users.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    email = models.EmailField(unique=True)

    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)

    REQUIRED_FIELDS = []
    USERNAME_FIELD = "email"

    def __str__(self):
        return self.email