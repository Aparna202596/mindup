from functools import wraps
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from django.views.decorators.cache import never_cache


# ── Helpers ────────────────────────────────────────────────────────────────────

def _apply_no_cache(response):
    """Force browser to never cache this response."""
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"]        = "no-cache"
    response["Expires"]       = "0"
    return response


# ── Function-based view decorators ─────────────────────────────────────────────

def admin_login_required(view_func):
    @never_cache
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/accounts/login/?next={request.path}")
        if not request.user.is_superuser:
            raise PermissionDenied
        response = view_func(request, *args, **kwargs)
        return _apply_no_cache(response)
    return wrapper


def user_login_required(perm=None):
    def decorator(view_func):
        @never_cache
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"/accounts/login/?next={request.path}")
            if perm and not request.user.is_superuser:
                if not request.user.has_perm(perm):
                    raise PermissionDenied
            response = view_func(request, *args, **kwargs)
            return _apply_no_cache(response)
        return wrapper
    return decorator


# ── Class-based view mixins ─────────────────────────────────────────────────────

class AdminLoginRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/accounts/login/?next={request.path}")
        if not request.user.is_superuser:
            raise PermissionDenied
        response = super().dispatch(request, *args, **kwargs)
        return _apply_no_cache(response)


class UserLoginRequiredMixin:
    required_permission: str | None = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/accounts/login/?next={request.path}")
        if self.required_permission and not request.user.is_superuser:
            if not request.user.has_perm(self.required_permission):
                raise PermissionDenied
        response = super().dispatch(request, *args, **kwargs)
        return _apply_no_cache(response)