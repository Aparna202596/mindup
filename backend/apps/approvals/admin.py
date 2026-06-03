from django.contrib import admin
from apps.approvals.models import ApprovalQueue

@admin.register(ApprovalQueue)
class ApprovalQueueAdmin(admin.ModelAdmin):

    list_display = (
        "object_type",
        "requested_by",
        "status",
        "reviewed_by",
        )
