"""Functions to protect access to views."""

from django.conf import settings
from django.contrib.auth import authenticate
from django.core.exceptions import PermissionDenied

from pytigon_lib.schviews.viewtools import render_to_response
from pytigon_lib.schdjangoext.django_init import get_app_name

_ANONYMOUS = None


def filter_by_permissions(view, model, queryset_or_obj, request):
    """Filter queryset or object based on model permissions."""
    if hasattr(model, "filter_by_permissions"):
        return model.filter_by_permissions(view, queryset_or_obj, request)
    return queryset_or_obj


def has_the_right(perm, model, param, request):
    """Check if the user has the right to perform an action on the model."""
    if hasattr(model, "has_the_right"):
        return model.has_the_right(perm, param, request)
    return True


def get_anonymous():
    """Retrieve or create an anonymous user."""
    global _ANONYMOUS
    if not _ANONYMOUS:
        _ANONYMOUS = authenticate(username="AnonymousUser", password="AnonymousUser")
    return _ANONYMOUS


def default_block(request):
    """Render a default block page when access is denied."""
    return render_to_response(
        "schsys/no_perm.html", context={}, request=request, status=401
    )


def make_perms_url_test_fun(app_name, fun, if_block_view=default_block):
    """Create a permission test function based on URL permissions."""
    app = None
    appbase = None
    perms = None
    perm_for_url = None

    for _app in settings.INSTALLED_APPS:
        pos = get_app_name(_app)
        if app_name in pos:
            app = pos
            break

    if app:
        elements = app.split(".")
        appbase = elements[-1]
        try:
            module = __import__(elements[0])
            if len(elements) > 1:
                module2 = getattr(module, elements[-1])
                if module2:
                    module3 = getattr(module2, "models")
                    if module3:
                        perms = module3.Perms
                        if hasattr(perms, "PermsForUrl"):
                            perm_for_url = perms.PermsForUrl
        except ImportError:
            pass

    def perms_test(request, *args, **kwargs):
        """Test permissions for the given request."""
        if perm_for_url:
            perm = perm_for_url(request.path)
            user = request.user
            if not user.is_authenticated:
                user = get_anonymous()
                if not user:
                    user = request.user
            if not user.has_perm(f"{appbase}.{perm}"):
                return if_block_view(request)
        return fun(request, app_name, *args, **kwargs)

    return perms_test


def make_perms_test_fun(app, model, perm, fun, if_block_view=default_block):
    """Create a permission test function for a specific permission."""

    def perms_test(request, *args, **kwargs):
        """Test permissions for the given request."""
        user = request.user
        if not user.is_authenticated:
            user = get_anonymous()
            if not user:
                user = request.user

        if not user.has_perm(perm):
            return if_block_view(request)
        if not has_the_right(perm, model, kwargs, request):
            return if_block_view(request)
        return fun(request, *args, **kwargs)

    return perms_test
