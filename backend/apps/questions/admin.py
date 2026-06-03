from django.contrib import admin
from apps.questions.models import Question

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):

    list_display = (
        "title",
        "created_by",
        "view_count"
    )

    search_fields = (
        "title",
    )
