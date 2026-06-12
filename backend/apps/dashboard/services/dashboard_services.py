from apps.core.models import (
    CustomUser, Topic, Category, SubCategory,
    Question, Answer, AnswerPoint,
    ApprovalQueue, BulkUploadSession,
)

def get_dashboard_stats() -> dict:
    return {
        "users": CustomUser.objects.count(),
        "topics": Topic.objects.count(),
        "categories": Category.objects.count(),
        "subcategories": SubCategory.objects.count(),
        "questions": Question.objects.count(),
        "answers": Answer.objects.count(),
        "answer_points": AnswerPoint.objects.count(),
        "pending_approvals": ApprovalQueue.objects.filter(is_approved__isnull=True).count(),
        "bulk_uploads": BulkUploadSession.objects.count(),
        "most_viewed": Question.objects.order_by("-view_count")[:5],
        "recent_bulk_uploads": (
            BulkUploadSession.objects
            .select_related("uploaded_by", "subcategory__category__topic")
            .order_by("-created_at")[:5]
        ),
    }