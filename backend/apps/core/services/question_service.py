from apps.core.models import Question
from .duplicate_detector import normalize_question, find_similar_questions


def create_question(*, user, subcategory, title):
    duplicates = find_similar_questions(title)
    if duplicates:
        return {"success": False, "duplicates": duplicates}

    question = Question.objects.create(
        subcategory=subcategory,
        title=title,
        normalized_title=normalize_question(title),
        created_by=user,
    )
    return {"success": True, "question": question}