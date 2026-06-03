from django import forms

from apps.questions.models import Question

from apps.core.validators import (
    validate_question_length
)

class QuestionForm(forms.ModelForm):

    class Meta:

        model = Question

        fields = [
            "subcategory",
            "title"
        ]

    def clean_title(self):

        title = self.cleaned_data["title"]

        validate_question_length(title)

        return title