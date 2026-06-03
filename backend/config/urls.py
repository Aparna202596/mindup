from django.contrib import admin
from django.urls import path, include

urlpatterns = [

    path(
        "accounts/",
        include("allauth.urls")
    ),

    path(
        "topics/",
        include("apps.topics.urls")
    ),

    path(
        "categories/",
        include("apps.categories.urls")
    ),

    path(
        "questions/",
        include("apps.questions.urls")
    ),

    path(
        "answers/",
        include("apps.answers.urls")
    ),
]
