from django.urls import path
from apps.dashboard import views

urlpatterns = [
    path("admin-dashboard/", views.admin_dashboard, name="admin-dashboard"),
    path("admin-dashboard/approve/<uuid:pk>/", views.approve_item, name="approve-item"),
]