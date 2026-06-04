from django.db.models import Q
from apps.core.models import Question, Topic, Category, SubCategory


def global_search(query):
    questions = Question.objects.filter(
        Q(title__icontains=query) |
        Q(normalized_title__icontains=query)
    ).select_related("subcategory__category__topic")[:20]

    topics = Topic.objects.filter(name__icontains=query, status="approved")[:5]
    categories = Category.objects.filter(name__icontains=query, status="approved")[:5]

    return {
        "questions": questions,
        "topics": topics,
        "categories": categories,
    }