from django.contrib import admin

from apps.categories.models import Category, SubCategory

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "topic",
        "status"
    )
