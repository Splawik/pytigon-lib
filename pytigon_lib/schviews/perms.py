"""Permission-checking utilities for the schviews module.

Provides functions and wrapper factories that protect views by
verifying user permissions and model-level access rights before
allowing view execution. Integrates with the Django authentication
system and optional CANCAN-style access control.
"""

import logging
import threading
from collections.abc import Callable
from typing import Any, Optional

from django.conf import settings
from django.contrib.auth import authenticate
from django.http import HttpRequest, HttpResponse

from pytigon_lib.schdjangoext.django_init import get_app_name
from pytigon_lib.schviews.viewtools import render_to_response

logger = logging.getLogger(__name__)

_ANONYMOUS: Optional[Any] = None
_ANONYMOUS_LOCK = threading.Lock()


def filter_by_permissions(
    view: Any,
    model: Any,
    queryset_or_obj: Any,
    request: HttpRequest,
) -> Any:
    """Filter a queryset or object based on the model's permission logic.

    Delegates to ``model.filter_by_permissions`` if available, otherwise
    returns the queryset/object unchanged.

    Args:
        view: The current view instance.
        model: The Django model class.
        queryset_or_obj: The queryset or object to filter.
        request: The incoming HTTP request.

    Returns:
        The filtered queryset or object.
    """
    if hasattr(model, "filter_by_permissions"):
        return model.filter_by_permissions(view, queryset_or_obj, request)
    return queryset_or_obj


def has_the_right(
    perm: str,
    model: Any,
    param: Any,
    request: HttpRequest,
) -> bool:
    """Check if the current user has the right to perform an action on a model.

    Delegates to ``model.has_the_right`` if available; otherwise returns
    ``True`` (permissive by default, relying on Django's standard
    permission system).

    Args:
        perm: The permission string being tested (e.g. ``'view'``, ``'change'``).
        model: The Django model class.
        param: Additional parameters (e.g. URL kwargs).
        request: The incoming HTTP request.

    Returns:
        ``True`` if the action is allowed, ``False`` otherwise.
    """
    if hasattr(model, "has_the_right"):
        return model.has_the_right(perm, param, request)
    return True


def get_anonymous() -> Any:
    """Retrieve or create a cached anonymous user instance.

    Thread-safe: uses double-checked locking to prevent multiple
    simultaneous authentications of the anonymous user.

    Returns:
        The anonymous User instance, or ``None`` if authentication fails.
    """
    global _ANONYMOUS
    if _ANONYMOUS is None:
        with _ANONYMOUS_LOCK:
            if _ANONYMOUS is None:
                try:
                    _ANONYMOUS = authenticate(
                        username="AnonymousUser", password="AnonymousUser"
                    )
                except Exception:
                    logger.warning(
                        "Failed to authenticate AnonymousUser; "
                        "permission checks may behave unexpectedly."
                    )
    return _ANONYMOUS


def default_block(request: HttpRequest) -> HttpResponse:
    """Render the default access-denied page.

    Args:
        request: The incoming HTTP request.

    Returns:
        An HttpResponse with status 401 and the 'no permission' template.
    """
    return render_to_response(
        "schsys/no_perm.html", context={}, request=request, status=401
    )


def make_perms_url_test_fun(
    app_name: str,
    fun: Callable,
    if_block_view: Callable = default_block,
) -> Callable:
    """Create a view wrapper that checks URL-based permissions.

    Looks up the application's ``Perms.PermsForUrl`` class in the
    models module and, if found, verifies that the current user (or the
    anonymous user) has the permission required for the requested URL path.

    Args:
        app_name: The short application name to look up in
            ``INSTALLED_APPS``.
        fun: The view function to protect.
        if_block_view: Callable that returns an HttpResponse when access
            is denied. Defaults to :func:`default_block`.

    Returns:
        A wrapper view function that performs permission checks before
        calling *fun*.
    """
    app = None
    appbase = None
    perm_for_url = None

    # Resolve the full dotted application label from the short name.
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
        except (ImportError, AttributeError):
            logger.debug(
                "Could not load PermsForUrl for app '%s'.", app_name, exc_info=True
            )

    def perms_test(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Permission-checking wrapper for URL-based access control."""
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


def make_perms_test_fun(
    app: str,
    model: Any,
    perm: str,
    fun: Callable,
    if_block_view: Callable = default_block,
) -> Callable:
    """Create a view wrapper that checks a specific model permission.

    Verifies that the current user (or anonymous user) holds the given
    Django permission string and passes the model-level
    :func:`has_the_right` check before allowing the view to execute.

    If the request has no ``user`` attribute (e.g. internal calls),
    the permission check is skipped entirely.

    Args:
        app: The application name (not used directly in checks, but
            passed through for compatibility).
        model: The Django model class for permission resolution.
        perm: The full Django permission string
            (e.g. ``'myapp.view_mymodel'``).
        fun: The view function to protect.
        if_block_view: Callable that returns an HttpResponse when access
            is denied. Defaults to :func:`default_block`.

    Returns:
        A wrapper view function with permission checking.
    """

    def perms_test(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        """Permission-checking wrapper for model-level access control."""
        if not hasattr(request, "user"):
            return fun(request, *args, **kwargs)
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
