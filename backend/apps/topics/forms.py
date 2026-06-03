from django import forms

from apps.topics.models import Topic

from apps.core.validators import (
    validate_no_special_only
)

class TopicForm(forms.ModelForm):

    class Meta:
        model = Topic

        fields = [
            "name",
            "description"
        ]

    def clean_name(self):

        name = self.cleaned_data["name"]

        validate_no_special_only(name)

        return name