"""Integration helpers for django-rules object-level permissions.

Provides thin wrappers that replace the django-cancan ``request.ability``
API with django-rules ``user.has_perm(perm, obj)`` calls, plus queryset
filtering support.

For large datasets, implement ``filter_by_permissions`` on the model
class to provide efficient queryset-level filtering instead of the
default per-object check used here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings
from django.db.models import Model, QuerySet

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractBaseUser

_RULES_IMPORTED: bool | None = None


def _ensure_rules() -> bool:
    """Check if the ``rules`` package is importable and cache the result."""
    global _RULES_IMPORTED
    if _RULES_IMPORTED is None:
        try:
            import rules  # noqa: F401
            _RULES_IMPORTED = True
        except ImportError:
            _RULES_IMPORTED = False
    return _RULES_IMPORTED


def is_rules_active() -> bool:
    """Return ``True`` when django-rules object-level permissions are enabled.

    Gates behaviour that previously checked ``hasattr(settings, "CANCAN")``.
    """
    if not _ensure_rules():
        return False
    return getattr(settings, "RULES_ENABLED", False)


def user_can(
    user: AbstractBaseUser | None,
    action: str,
    model: type[Model],
    obj: Model | None = None,
) -> bool:
    """Check whether *user* may perform *action* on *obj* (or *model* class).

    Constructs a django-rules permission codename from
    ``{app_label}.{action}_{model_name}`` and delegates to Django's
    ``user.has_perm()``, which django-rules extends with object-level
    predicate evaluation.

    Args:
        user: The authenticated user (or ``None`` / anonymous).
        action: Action name (e.g. ``"detail"``, ``"change"``, ``"view"``).
        model: Django model class (used for ``app_label`` / ``model_name``).
        obj: Optional object instance for object-level checks.

    Returns:
        ``True`` if the permission is granted.
    """
    if user is None or not user.is_authenticated:
        return False
    perm = _make_perm(action, model)
    return user.has_perm(perm, obj)


def filter_queryset_by_rules(
    user: AbstractBaseUser | None,
    action: str,
    model: type[Model],
    queryset: QuerySet | None = None,
) -> QuerySet:
    """Return a queryset filtered to objects the user may perform *action* on.

    Falls back to the full unfiltered queryset when django-rules is not
    active or the user has no relevant permission registered.

    Note:
        Uses per-object ``user.has_perm()`` filtering.  For large tables
        implement ``filter_by_permissions`` on the model for efficient
        queryset-level access control.

    Args:
        user: The authenticated user (or ``None`` / anonymous).
        action: Action name (e.g. ``"view"``).
        model: Django model class.
        queryset: Optional base queryset; defaults to ``model.objects.all()``.

    Returns:
        A ``QuerySet`` filtered to accessible objects.
    """
    if queryset is None:
        queryset = model.objects.all()

    if not is_rules_active() or user is None or not user.is_authenticated:
        return queryset

    perm = _make_perm(action, model)

    import rules
    if not rules.perm_exists(perm):
        return queryset

    allowed_pks = [obj.pk for obj in queryset if user.has_perm(perm, obj)]
    return model.objects.filter(pk__in=allowed_pks)


def _make_perm(action: str, model: type[Model]) -> str:
    """Build a django permission codename from an action and a model class.

    Example: ``_make_perm("change", MyModel)`` → ``"myapp.change_mymodel"``.
    """
    app_label = model._meta.app_label
    model_name = model._meta.model_name
    return f"{app_label}.{action}_{model_name}"
