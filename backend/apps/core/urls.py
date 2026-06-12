from django.urls import path
from apps.core  import views

urlpatterns = [
    # ── Home & Auth ────────────────────────────────────────────────────────
    path("", views.home, name="home"),
    path("login-redirect/", views.smart_login_redirect, name="smart-login-redirect"),
    path("search/", views.search_view, name="search"),

    # ── AJAX (dynamic selects) ─────────────────────────────────────────────
    path("ajax/categories/", views.ajax_load_categories, name="ajax-categories"),
    path("ajax/subcategories/", views.ajax_load_subcategories, name="ajax-subcategories"),

    # ── Topics ─────────────────────────────────────────────────────────────
    path("topics/", views.TopicListView.as_view(), name="topic-list"),
    path("topics/create/", views.TopicCreateView.as_view(), name="topic-create"),
    path("topics/<uuid:pk>/", views.TopicDetailView.as_view(), name="topic-detail"),
    path("topics/<uuid:pk>/edit/", views.topic_edit, name="topic-edit"),
    path("topics/<uuid:pk>/delete/", views.topic_delete, name="topic-delete"),

    # ── Categories ─────────────────────────────────────────────────────────
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path("categories/create/", views.CategoryCreateView.as_view(), name="category-create"),
    path("categories/<uuid:pk>/", views.CategoryDetailView.as_view(), name="category-detail"),
    path("categories/<uuid:pk>/edit/", views.category_edit, name="category-edit"),
    path("categories/<uuid:pk>/delete/", views.category_delete, name="category-delete"),
    # Inline subcategory creation from a category page
    path("categories/<uuid:category_pk>/add-subcategory/", views.subcategory_create, name="subcategory-create-under"),

    # ── Subcategories ──────────────────────────────────────────────────────
    path("subcategories/create/", views.subcategory_create, name="subcategory-create"),
    path("subcategories/<uuid:pk>/", views.SubCategoryDetailView.as_view(), name="subcategory-detail"),
    path("subcategories/<uuid:pk>/edit/", views.subcategory_edit, name="subcategory-edit"),
    path("subcategories/<uuid:pk>/delete/", views.subcategory_delete, name="subcategory-delete"),

    # ── Questions ──────────────────────────────────────────────────────────
    path("questions/", views.QuestionListView.as_view(), name="question-list"),
    path("questions/create/", views.question_create_view, name="question-create"),
    path("questions/bulk/", views.bulk_qa_upload, name="bulk-qa-upload"),
    path("questions/<uuid:pk>/", views.QuestionDetailView.as_view(), name="question-detail"),
    path("questions/<uuid:pk>/edit/", views.question_edit, name="question-edit"),
    path("questions/<uuid:pk>/delete/", views.question_delete, name="question-delete"),

    # ── Answers ────────────────────────────────────────────────────────────
    path("questions/<uuid:question_pk>/answer/", views.answer_create_view, name="answer-create"),
    path("answers/<uuid:pk>/edit/", views.answer_edit, name="answer-edit"),
    path("answers/<uuid:pk>/delete/", views.answer_delete, name="answer-delete"),
    path("answers/<uuid:answer_pk>/point/", views.answer_point_create_view, name="answerpoint-create"),

    # ── User Dashboard ─────────────────────────────────────────────────────
    path("dashboard/", views.user_dashboard, name="user-dashboard"),
    path("notifications/<uuid:pk>/read/", views.mark_notification_read, name="notification-read"),
    path("notifications/read-all/", views.mark_all_notifications_read, name="notification-read-all"),

    # ── Admin views ────────────────────────────────────────────────────────
    path("audit-log/", views.audit_log_view, name="audit-log"),
    path("admin-content/", views.admin_content_view, name="admin-content"),
    path("users/", views.user_list_view, name="user-list"),
    path("users/<uuid:pk>/role/", views.user_role_update, name="user-role-update"),
]