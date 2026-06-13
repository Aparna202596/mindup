from django.urls import path
from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.contrib import messages as _msgs

from apps.core import views
from apps.core.forms import TopicForm
from apps.core.decorators import UserLoginRequiredMixin
from apps.core.models import Topic as _Topic


class _TopicCreateView(UserLoginRequiredMixin, CreateView):
    model         = _Topic
    form_class    = TopicForm
    template_name = "topics/topic_create.html"
    success_url   = reverse_lazy("topic-list")

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        _msgs.success(self.request, "Topic submitted for approval.")
        return super().form_valid(form)


urlpatterns = [
    # ── Home & Auth ────────────────────────────────────────────────────────
    path("", views.home, name="home"),
    path("login-redirect/", views.smart_login_redirect, name="smart-login-redirect"),
    path("search/", views.search_view, name="search"),

    # ── AJAX dynamic selects ──────────────────────────────────────────────
    path("ajax/categories/",    views.ajax_load_categories,    name="ajax-categories"),
    path("ajax/subcategories/", views.ajax_load_subcategories, name="ajax-subcategories"),

    # ── Favorites ─────────────────────────────────────────────────────────
    path("favorites/",      views.favorites_page,  name="favorites"),
    path("ajax/favorites/", views.toggle_favorite, name="toggle-favorite"),

    # ══════════════════════════════════════════════════════════════════════
    # TOPICS
    # ══════════════════════════════════════════════════════════════════════
    path("topics/",                  views.topic_list_view,           name="topic-list"),
    path("topics/create/",           _TopicCreateView.as_view(),      name="topic-create"),
    path("topics/<uuid:pk>/",        views.topic_detail_view,         name="topic-detail"),
    path("topics/<uuid:pk>/edit/",   views.topic_edit,                name="topic-edit"),
    path("topics/<uuid:pk>/delete/", views.topic_delete,              name="topic-delete"),

    # AJAX endpoints — topics
    path("ajax/topics/create/",           views.topic_create_ajax,  name="ajax-topic-create"),
    path("ajax/topics/<uuid:pk>/edit/",   views.topic_edit_ajax,    name="ajax-topic-edit"),
    path("ajax/topics/<uuid:pk>/hide/",   views.topic_hide_ajax,    name="ajax-topic-hide"),
    path("ajax/topics/<uuid:pk>/unhide/", views.topic_unhide_ajax,  name="ajax-topic-unhide"),
    path("ajax/topics/<uuid:pk>/delete/", views.topic_delete_ajax,  name="ajax-topic-delete"),

    # ══════════════════════════════════════════════════════════════════════
    # CATEGORIES
    # ══════════════════════════════════════════════════════════════════════
    path("categories/",                  views.category_list_view,   name="category-list"),
    path("categories/create/",           views.category_create_ajax, name="category-create"),
    path("categories/<uuid:pk>/",        views.category_detail_view, name="category-detail"),
    path("categories/<uuid:pk>/edit/",   views.category_edit,        name="category-edit"),
    path("categories/<uuid:pk>/delete/", views.category_delete,      name="category-delete"),

    path("categories/<uuid:category_pk>/add-subcategory/",
         views.subcategory_create, name="subcategory-create-under"),

    # AJAX endpoints — categories
    path("ajax/categories/create/",           views.category_create_ajax,  name="ajax-category-create"),
    path("ajax/categories/<uuid:pk>/edit/",   views.category_edit_ajax,    name="ajax-category-edit"),
    path("ajax/categories/<uuid:pk>/hide/",   views.category_hide_ajax,    name="ajax-category-hide"),
    path("ajax/categories/<uuid:pk>/unhide/", views.category_unhide_ajax,  name="ajax-category-unhide"),
    path("ajax/categories/<uuid:pk>/delete/", views.category_delete_ajax,  name="ajax-category-delete"),

    # ══════════════════════════════════════════════════════════════════════
    # SUBCATEGORIES
    # ══════════════════════════════════════════════════════════════════════
    path("subcategories/create/",           views.subcategory_create,       name="subcategory-create"),
    path("subcategories/<uuid:pk>/",        views.subcategory_detail_view,  name="subcategory-detail"),
    path("subcategories/<uuid:pk>/edit/",   views.subcategory_edit,         name="subcategory-edit"),
    path("subcategories/<uuid:pk>/delete/", views.subcategory_delete,       name="subcategory-delete"),

    # AJAX endpoints — subcategories
    path("ajax/subcategories/create/",           views.subcategory_create_ajax,  name="ajax-subcategory-create"),
    path("ajax/subcategories/<uuid:pk>/edit/",   views.subcategory_edit_ajax,    name="ajax-subcategory-edit"),
    path("ajax/subcategories/<uuid:pk>/hide/",   views.subcategory_hide_ajax,    name="ajax-subcategory-hide"),
    path("ajax/subcategories/<uuid:pk>/unhide/", views.subcategory_unhide_ajax,  name="ajax-subcategory-unhide"),
    path("ajax/subcategories/<uuid:pk>/delete/", views.subcategory_delete_ajax,  name="ajax-subcategory-delete"),

    # ══════════════════════════════════════════════════════════════════════
    # QUESTIONS
    # ══════════════════════════════════════════════════════════════════════
    path("questions/",                  views.question_list_view,   name="question-list"),
    path("questions/create/",           views.question_create_view, name="question-create"),
    path("questions/bulk/",             views.bulk_qa_upload,       name="bulk-qa-upload"),
    path("questions/<uuid:pk>/",        views.question_detail_view, name="question-detail"),
    path("questions/<uuid:pk>/edit/",   views.question_edit,        name="question-edit"),
    path("questions/<uuid:pk>/delete/", views.question_delete,      name="question-delete"),

    # AJAX endpoints — questions
    path("ajax/questions/create/",           views.question_create_ajax, name="ajax-question-create"),
    path("ajax/questions/<uuid:pk>/edit/",   views.question_edit_ajax,   name="ajax-question-edit"),
    path("ajax/questions/<uuid:pk>/hide/",   views.question_hide_ajax,   name="ajax-question-hide"),
    path("ajax/questions/<uuid:pk>/unhide/", views.question_unhide_ajax, name="ajax-question-unhide"),
    path("ajax/questions/<uuid:pk>/delete/", views.question_delete_ajax, name="ajax-question-delete"),

    # ── Answers ────────────────────────────────────────────────────────────
    path("questions/<uuid:question_pk>/answer/", views.answer_create_view,      name="answer-create"),
    path("answers/<uuid:pk>/edit/",              views.answer_edit,              name="answer-edit"),
    path("answers/<uuid:pk>/delete/",            views.answer_delete,            name="answer-delete"),
    path("answers/<uuid:answer_pk>/point/",      views.answer_point_create_view, name="answerpoint-create"),

    # ── User Dashboard ─────────────────────────────────────────────────────
    path("dashboard/",                    views.user_dashboard,              name="user-dashboard"),
    path("notifications/<uuid:pk>/read/", views.mark_notification_read,      name="notification-read"),
    path("notifications/read-all/",       views.mark_all_notifications_read, name="notification-read-all"),

    # ── Admin views ────────────────────────────────────────────────────────
    path("audit-log/",            views.audit_log_view,    name="audit-log"),
    path("admin-content/",        views.admin_content_view, name="admin-content"),
    path("users/",                views.user_list_view,    name="user-list"),
    path("users/<uuid:pk>/role/", views.user_role_update,  name="user-role-update"),
]