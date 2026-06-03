from django import forms

from apps.answers.models import Answer, AnswerPoint

class AnswerForm(forms.ModelForm):

    class Meta:

        model = Answer

        fields = [
            "content"
        ]

class AnswerPointForm(forms.ModelForm):

    class Meta:

        model = AnswerPoint

        fields = [
            "point"
        ]