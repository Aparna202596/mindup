from django.urls import path

from .views import (
    AnswerCreateView,
    AnswerListView,
    AnswerDetailView,
    AnswerPointCreateView,
    AnswerPointListView
)

urlpatterns = [
    path("", AnswerListView.as_view(), name="answer-list"),

    path(
        "create/",
        AnswerCreateView.as_view(),
        name="answer-create"
    ),

    path(
        "<uuid:pk>/",
        AnswerDetailView.as_view(),
        name="answer-detail"
    ),

    path(
        "points/",
        AnswerPointListView.as_view(),
        name="answerpoint-list"
    ),

    path(
        "points/create/",
        AnswerPointCreateView.as_view(),
        name="answerpoint-create"
    ),
]