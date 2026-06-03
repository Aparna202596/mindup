from django.urls import path

from .views import (
    CategoryCreateView,
    CategoryListView,
    CategoryDetailView,
    SubCategoryCreateView,
    SubCategoryListView,
    SubCategoryDetailView,
)

urlpatterns = [
    path("", CategoryListView.as_view(), name="category-list"),
    path("create/", CategoryCreateView.as_view(), name="category-create"),
    path("<uuid:pk>/", CategoryDetailView.as_view(), name="category-detail"),

    path(
        "subcategories/",
        SubCategoryListView.as_view(),
        name="subcategory-list"
    ),

    path(
        "subcategories/create/",
        SubCategoryCreateView.as_view(),
        name="subcategory-create"
    ),

    path(
        "subcategories/<uuid:pk>/",
        SubCategoryDetailView.as_view(),
        name="subcategory-detail"
    ),
]