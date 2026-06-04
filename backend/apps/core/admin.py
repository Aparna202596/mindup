from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from apps.core.models import (
    CustomUser, Role, Topic, Category, SubCategory,
    Question, Answer, AnswerPoint, PDFUpload,
    ApprovalQueue, Notification, AuditLog,
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ("email", "role", "is_staff", "date_joined")
    search_fields = ("email",)
    ordering = ("email",)
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Role", {"fields": ("role",)}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser")}),
    )
    add_fieldsets = (
        (None, {"fields": ("email", "password1", "password2")}),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name",)


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "created_by", "created_at")
    search_fields = ("name",)
    list_filter = ("status",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "topic", "status", "created_by")
    list_filter = ("status",)


@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "status")
    list_filter = ("status",)


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("title", "created_by", "view_count", "created_at")
    search_fields = ("title",)


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ("question", "created_by", "upvotes", "created_at")


@admin.register(AnswerPoint)
class AnswerPointAdmin(admin.ModelAdmin):
    list_display = ("answer", "created_by", "created_at")


@admin.register(PDFUpload)
class PDFUploadAdmin(admin.ModelAdmin):
    list_display = ("uploaded_by", "process_status", "created_at")
    list_filter = ("process_status",)


@admin.register(ApprovalQueue)
class ApprovalQueueAdmin(admin.ModelAdmin):
    list_display = ("object_type", "requested_by", "is_approved", "reviewed_by")
    list_filter = ("object_type", "is_approved")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "title", "is_read", "created_at")
    list_filter = ("is_read",)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("user", "action", "object_type", "created_at")
    list_filter = ("action", "object_type")
    readonly_fields = ("user", "action", "object_type", "object_id", "previous_data", "new_data", "created_at")