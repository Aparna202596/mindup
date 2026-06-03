from django.contrib import admin
from apps.uploads.models import PDFUpload
@admin.register(PDFUpload)
class PDFUploadAdmin(admin.ModelAdmin):

    list_display = (
        "uploaded_by",
        "process_status",
        "created_at"
    )
