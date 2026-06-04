import re
from django.core.exceptions import ValidationError


def validate_no_special_only(value):
    cleaned = re.sub(r'[^A-Za-z0-9]', '', value)
    if not cleaned:
        raise ValidationError("Content cannot contain only special characters.")


def validate_question_length(value):
    if len(value.strip()) < 10:
        raise ValidationError("Question must be at least 10 characters.")


def validate_answer_length(value):
    if len(value.strip()) < 20:
        raise ValidationError("Answer must be at least 20 characters.")


def validate_pdf_extension(value):
    import os
    ext = os.path.splitext(value.name)[1].lower()
    if ext != '.pdf':
        raise ValidationError("Only PDF files are allowed.")