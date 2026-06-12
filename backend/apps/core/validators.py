import re
from django.core.exceptions import ValidationError


def validate_no_special_only(value: str) -> None:
    """Reject strings that contain only special characters."""
    cleaned = re.sub(r"[^A-Za-z0-9]", "", value)
    if not cleaned:
        raise ValidationError("Content cannot contain only special characters.")


def validate_question_length(value: str) -> None:
    if len(value.strip()) < 10:
        raise ValidationError("Question must be at least 10 characters.")


def validate_answer_length(value: str) -> None:
    if len(value.strip()) < 5:
        raise ValidationError("Answer must be at least 5 characters.")