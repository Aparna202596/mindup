from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages
from django.http import JsonResponse

from apps.dashboard.services.dashboard_services import get_dashboard_stats
from apps.core.models import (
    ApprovalQueue, Topic, Category, SubCategory,
    Question, Answer, BulkUploadSession,
)
from apps.core.services.notification_service import create_notification
from apps.core.services.audit_service import create_audit_log
from apps.core.decorators import admin_login_required

TAB_LIST = [
    ("topics",       "Topics"),
    ("categories",   "Categories"),
    ("subcategories","Subcategories"),
    ("questions",    "Questions"),
    ("answers",      "Answers"),
    ("bulk_uploads", "Bulk Uploads"),
]


@admin_login_required
def admin_dashboard(request):
    stats   = get_dashboard_stats()
    pending = (
        ApprovalQueue.objects
        .filter(is_approved__isnull=True)
        .select_related("requested_by")
        .order_by("-created_at")
    )
    tab = request.GET.get("tab", "topics")

    tab_querysets = {
        "topics": lambda: Topic.objects.select_related("created_by").order_by("-created_at"),
        "categories": lambda: Category.objects.select_related("topic", "created_by").order_by("-created_at"),
        "subcategories": lambda: SubCategory.objects.select_related(
            "category__topic", "created_by"
        ).order_by("-created_at"),
        "questions": lambda: Question.objects.select_related(
            "subcategory__category__topic", "created_by"
        ).order_by("-created_at"),
        "answers": lambda: Answer.objects.select_related(
            "question", "created_by"
        ).order_by("-created_at"),
        "bulk_uploads": lambda: BulkUploadSession.objects.select_related(
            "uploaded_by", "subcategory__category__topic"
        ).order_by("-created_at"),
    }

    items = tab_querysets.get(tab, lambda: [])()

    return render(request, "dashboard/admin_dashboard.html", {
        "stats":    stats,
        "pending":  pending,
        "tab":      tab,
        "tab_list": TAB_LIST,
        "items":    items,
    })


@admin_login_required
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

    item.reviewed_by = request.user
    item.reviewed_at = timezone.now()
    item.save()
    return redirect("admin-dashboard")


def _set_status(item, status: str) -> None:
    model_map = {
        "topic":       Topic,
        "category":    Category,
        "subcategory": SubCategory,
    }
    Model = model_map.get(item.object_type)
    if Model:
        Model.objects.filter(pk=item.object_id).update(status=status)
