from django.core.exceptions import ValidationError
import re


def validate_no_special_only(value):

    cleaned = re.sub(r'[^A-Za-z0-9]', '', value)

    if not cleaned:
        raise ValidationError(
            "Content cannot contain only special characters."
        )
    
def validate_no_special_start(value):

    if value and re.match(r'^[^A-Za-z0-9]', value):
        raise ValidationError(
            "Content cannot start with a special character."
        )

def validate_question_length(value):

    if len(value.strip()) < 5:
        raise ValidationError(
            "Question is too short."
        )  
    
def validate_answer_length(value):

    if len(value.strip()) < 5:
        raise ValidationError(
            "Answer is too short."
        )
    
