from django.contrib import admin
from apps.core.models import AuditLog
@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "action",
        "object_type",
        "created_at"
    )
