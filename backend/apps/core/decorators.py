from functools import wraps
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied
from django.views.decorators.cache import never_cache
from django.contrib.auth.decorators import login_required


def admin_login_required(view_func):
    @never_cache
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/accounts/login/?next={request.path}")
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return wrapper


def user_login_required(perm=None):
    def decorator(view_func):
        @never_cache
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect(f"/accounts/login/?next={request.path}")
            if perm and not request.user.has_perm(perm):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class AdminLoginRequiredMixin:
    """CBV mixin equivalent of @admin_login_required."""
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/accounts/login/?next={request.path}")
        if not request.user.is_superuser:
            raise PermissionDenied
        response = super().dispatch(request, *args, **kwargs)
        # Apply never_cache headers
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response


class UserLoginRequiredMixin:
    """CBV mixin equivalent of @user_login_required."""
    required_permission = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/accounts/login/?next={request.path}")
        if self.required_permission and not request.user.has_perm(self.required_permission):
            raise PermissionDenied
        response = super().dispatch(request, *args, **kwargs)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response