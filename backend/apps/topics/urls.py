from django.urls import path

from .views import (
    TopicCreateView,
    TopicListView,
    TopicDetailView
)

urlpatterns = [

    path(
        "",
        TopicListView.as_view(),
        name="topic-list"
    ),

    path(
        "create/",
        TopicCreateView.as_view(),
        name="topic-create"
    ),

    path(
        "<uuid:pk>/",
        TopicDetailView.as_view(),
        name="topic-detail"
    ),
]