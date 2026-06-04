from apps.core.models import (
    CustomUser, Topic, Category, SubCategory,
    Question, Answer, AnswerPoint, PDFUpload, ApprovalQueue,
)


def get_dashboard_stats():
    return {
        "users": CustomUser.objects.count(),
        "topics": Topic.objects.count(),
        "categories": Category.objects.count(),
        "subcategories": SubCategory.objects.count(),
        "questions": Question.objects.count(),
        "answers": Answer.objects.count(),
        "answer_points": AnswerPoint.objects.count(),
        "pending_approvals": ApprovalQueue.objects.filter(is_approved__isnull=True).count(),
        "pdf_uploads": PDFUpload.objects.count(),
        "most_viewed": Question.objects.order_by("-view_count")[:5],
    }