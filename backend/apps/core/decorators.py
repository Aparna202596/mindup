from functools import wraps
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from django.views.decorators.cache import never_cache


# ── Helpers ────────────────────────────────────────────────────────────────────

def _apply_no_cache(response):
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response

def _login_url(path: str) -> str:
    return f"/accounts/login/?next={path}"


# ── Admin decorator ────────────────────────────────────────────────────────────

def admin_login_required(view_func):
    @never_cache
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(_login_url(request.path))
        if not request.user.is_superuser:
            raise PermissionDenied
        response = view_func(request, *args, **kwargs)
        return _apply_no_cache(response)
    return wrapper


# ── User decorator ─────────────────────────────────────────────────────────────

def user_login_required(perm=None):
    def decorator(view_func):
        @never_cache
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(_login_url(request.path))
            if perm and not request.user.is_superuser:
                if not request.user.has_perm(perm):
                    raise PermissionDenied
            response = view_func(request, *args, **kwargs)
            return _apply_no_cache(response)
        return wrapper
    return decorator


# ── Class-based view mixins ────────────────────────────────────────────────────
# CBV mixin: authenticated superuser, no-cache
class AdminLoginRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(_login_url(request.path))
        if not request.user.is_superuser:
            raise PermissionDenied
        response = super().dispatch(request, *args, **kwargs)
        return _apply_no_cache(response)

# CBV mixin: authenticated user, optional permission, no-cache
class UserLoginRequiredMixin:

    required_permission: str | None = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(_login_url(request.path))
        if self.required_permission and not request.user.is_superuser:
            if not request.user.has_perm(self.required_permission):
                raise PermissionDenied
        response = super().dispatch(request, *args, **kwargs)
        return _apply_no_cache(response)