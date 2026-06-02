from .duplicate_detector import (
    normalize_question,
    find_similar_questions
)

from apps.questions.models import Question

def create_question(*, user, subcategory, title):

    duplicates = find_similar_questions(title)

    if duplicates:

        return {
            "success": False,
            "duplicates": duplicates
        }

    normalized = normalize_question(title)

    question = Question.objects.create(
        subcategory=subcategory,
        title=title,
        normalized_title=normalized,
        created_by=user
    )

    return {
        "success": True,
        "question": question
    }