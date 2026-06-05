from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.contrib.auth import views as auth_views


admin.site.login_template = "admin/login.html"

def custom_admin_login(request, *args, **kwargs):
    """
    Wraps the default admin login view. If the user successfully logs in,
    they are redirected straight to the custom admin-dashboard.
    """
    if request.method == "POST" and request.user.is_authenticated:
        return redirect("admin-dashboard")
        
    response = admin.site.login(request, *args, **kwargs)
    
    # If a GET or failed POST request happened but they are already authenticated,
    # send them directly to the admin dashboard instead of the native index.
    if request.user.is_authenticated and response.status_code == 302:
        return redirect("admin-dashboard")
        
    return response

urlpatterns = [
    # Intercept the specific login route before loading regular admin urls
    path("admin/login/", custom_admin_login),
    path("admin/", admin.site.urls),
    
    path("accounts/", include("allauth.urls")),
    path("", include("apps.core.urls")),
    path("", include("apps.dashboard.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])