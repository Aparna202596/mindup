from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from django.contrib import messages

from apps.dashboard.services.dashboard_services import get_dashboard_stats
from apps.core.models import ApprovalQueue, Topic, Category, SubCategory
from apps.core.services.notification_service import create_notification
from apps.core.services.audit_service import create_audit_log
from apps.core.permissions import admin_required


@admin_required
def admin_dashboard(request):
    stats   = get_dashboard_stats()
    pending = ApprovalQueue.objects.filter(
        is_approved__isnull=True
    ).select_related("requested_by").order_by("-created_at")
    return render(request, "dashboard/admin_dashboard.html", {
        "stats": stats, "pending": pending,
    })


@admin_required
def approve_item(request, pk):
    if request.method != "POST":
        return redirect("admin-dashboard")

    item   = get_object_or_404(ApprovalQueue, pk=pk)
    action = request.POST.get("action")

    if action == "approve":
        item.is_approved = True
        _set_status(item, "approved")
        create_notification(
            user=item.requested_by,
            title=f"{item.object_type.title()} Approved",
            message=f"Your {item.object_type} has been approved and is now live.",
        )
        create_audit_log(
            user=request.user, action="APPROVE",
            object_type=item.object_type, object_id=item.object_id,
        )
        messages.success(request, f"{item.object_type.title()} approved.")

    elif action == "reject":
        item.is_approved = False
        _set_status(item, "rejected")
        create_notification(
            user=item.requested_by,
            title=f"{item.object_type.title()} Rejected",
            message=f"Your {item.object_type} submission was not approved.",
        )
        create_audit_log(
            user=request.user, action="REJECT",
            object_type=item.object_type, object_id=item.object_id,
        )
        messages.warning(request, f"{item.object_type.title()} rejected.")

    item.reviewed_by  = request.user
    item.reviewed_at  = timezone.now()
    item.save()
    return redirect("admin-dashboard")


def _set_status(item, status):
    model_map = {"topic": Topic, "category": Category, "subcategory": SubCategory}
    Model = model_map.get(item.object_type)
    if Model:
        Model.objects.filter(pk=item.object_id).update(status=status)