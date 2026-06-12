from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.contrib import messages

from apps.dashboard.services.dashboard_services import get_dashboard_stats
from apps.core.models import ApprovalQueue, Topic, Category, SubCategory, PDFUpload
from apps.core.models import Question, Answer
from apps.core.services.notification_service import create_notification
from apps.core.services.audit_service import create_audit_log
from core.decorators import admin_login_required, user_login_required
from django.views.decorators.cache import never_cache
from allauth.account import views as allauth_views


TAB_LIST = [
    ("topics",        "Topics"),
    ("categories",    "Categories"),
    ("subcategories", "Subcategories"),
    ("questions",     "Questions"),
    ("answers",       "Answers"),
    ("bulk_uploads",  "Bulk Uploads"),   
]


@admin_login_required
def admin_dashboard(request):
    stats = get_dashboard_stats()

    # All pending approval queue items (topics/categories/subcategories + pdf uploads)
    pending = (
        ApprovalQueue.objects
        .filter(is_approved__isnull=True)
        .select_related("requested_by")
        .order_by("-created_at")
    )

    # ── Content tab data ───────────────────────────────────────────────────────
    tab = request.GET.get("tab", "topics")

    if tab == "topics":
        items = Topic.objects.order_by("-created_at")
    elif tab == "categories":
        items = Category.objects.select_related("topic").order_by("-created_at")
    elif tab == "subcategories":
        items = SubCategory.objects.select_related("category__topic").order_by("-created_at")
    elif tab == "questions":
        items = Question.objects.select_related(
            "subcategory__category__topic", "created_by"
        ).order_by("-created_at")
    elif tab == "answers":
        items = Answer.objects.select_related("question", "created_by").order_by("-created_at")
    elif tab == "uploads":
        items = PDFUpload.objects.select_related("uploaded_by").order_by("-created_at")
    else:
        items = []

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

def _set_status(item, status):
    model_map = {
        "topic":       (Topic,      "status"),
        "category":    (Category,   "status"),
        "subcategory": (SubCategory,"status"),
        "pdf_upload":  (PDFUpload,  "process_status"),  
        "question":    (Question,   "status"),
        "answer":      (Answer,     "status"),
    }
    entry = model_map.get(item.object_type)
    if entry:
        Model, field = entry
        Model.objects.filter(pk=item.object_id).update(**{field: status})
