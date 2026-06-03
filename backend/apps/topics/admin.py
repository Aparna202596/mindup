from django.contrib import admin

from apps.topics.models import Topic

@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "status",
        "created_by",
        "created_at"
    )

    search_fields = (
        "name",
    )

    list_filter = (
        "status",
    )