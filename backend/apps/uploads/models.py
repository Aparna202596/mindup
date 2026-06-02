from django.db import models
from apps.core.models import TimeStampedModel
from apps.users.models import CustomUser


class PDFUpload(TimeStampedModel):

    PROCESSING_STATUS = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("completed", "Completed"),
        ("failed", "Failed"),
    ]

    file = models.FileField(upload_to="pdfs/")

    uploaded_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE)

    process_status = models.CharField(max_length=20, choices=PROCESSING_STATUS, default="pending")

    processing_report = models.TextField(blank=True, null=True)
