from django.urls import path
from apps.core import views

urlpatterns = [
    path("", views.home, name="home"),
    path("search/", views.search_view, name="search"),

    # Topics
    path("topics/", views.TopicListView.as_view(), name="topic-list"),
    path("topics/create/", views.TopicCreateView.as_view(), name="topic-create"),
    path("topics/<uuid:pk>/", views.TopicDetailView.as_view(), name="topic-detail"),

    # Categories
    path("categories/", views.CategoryListView.as_view(), name="category-list"),
    path("categories/create/", views.CategoryCreateView.as_view(), name="category-create"),
    path("categories/<uuid:pk>/", views.CategoryDetailView.as_view(), name="category-detail"),

    # Subcategories
    path("subcategories/create/", views.SubCategoryCreateView.as_view(), name="subcategory-create"),
    path("subcategories/<uuid:pk>/", views.SubCategoryDetailView.as_view(), name="subcategory-detail"),

    # Questions
    path("questions/", views.QuestionListView.as_view(), name="question-list"),
    path("questions/create/", views.question_create_view, name="question-create"),
    path("questions/<uuid:pk>/", views.QuestionDetailView.as_view(), name="question-detail"),

    # Answers
    path("questions/<uuid:question_pk>/answer/", views.answer_create_view, name="answer-create"),
    path("answers/<uuid:answer_pk>/point/", views.answer_point_create_view, name="answerpoint-create"),

    # Uploads
    path("upload/", views.pdf_upload_view, name="pdf-upload"),
    path("upload/history/", views.upload_history_view, name="upload-history"),

    # User dashboard
    path("dashboard/", views.user_dashboard, name="user-dashboard"),
    path("notifications/<uuid:pk>/read/", views.mark_notification_read, name="notification-read"),
]