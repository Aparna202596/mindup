from django.contrib import admin
from apps.answers.models import Answer
@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):

    list_display = (
        "question",
        "created_by",
        "created_at"
    )
