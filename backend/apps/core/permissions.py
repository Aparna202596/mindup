from django.core.exceptions import PermissionDenied
from functools import wraps


def admin_required(view_func):
    """Decorator: requires user.is_admin (superuser or Admin role)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect(f"/accounts/login/?next={request.path}")
        if not request.user.is_admin:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


class AdminRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.shortcuts import redirect
            return redirect(f"/accounts/login/?next={request.path}")
        if not request.user.is_admin:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)