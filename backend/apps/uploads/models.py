from django.db import models
from apps.core.models import TimeStampedModel
from apps.users.models import CustomUser


class PDFUpload(TimeStampedModel):

    file = models.FileField(upload_to="pdfs/")

    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    processed = models.BooleanField(default=False)

    processing_report = models.TextField(blank=True, null=True)