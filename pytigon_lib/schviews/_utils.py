"""Internal utilities for schviews — avoids circular imports."""

import datetime
from typing import Any

import django
from django.conf import settings
from django.urls import reverse
from django.utils.functional import lazy


def make_path(view_name: str, args: list[Any] | None = None) -> str:
    if settings.URL_ROOT_FOLDER:
        return f"{settings.URL_ROOT_FOLDER}/{reverse(view_name, args=args)}"
    return reverse(view_name, args=args)


make_path_lazy = lazy(make_path, str)


def _isinstance(field: Any, instances: list[type]) -> bool:
    """Return ``True`` if *field* is an instance of any type in *instances*."""
    return any(isinstance(field, instance) for instance in instances)


def convert_str_to_model_field(s: str, field: Any) -> Any:
    if _isinstance(field, (django.db.models.CharField, django.db.models.TextField)):
        return s
    if _isinstance(field, (django.db.models.DateTimeField,)):
        return datetime.datetime.fromisoformat(s[:19])
    if _isinstance(field, (django.db.models.DateField,)):
        return datetime.date.fromisoformat(s)
    if _isinstance(field, (django.db.models.FloatField,)):
        return float(s)
    if _isinstance(
        field, (django.db.models.IntegerField, django.db.models.BigAutoField)
    ):
        return int(s)
    if _isinstance(field, (django.db.models.BooleanField,)):
        return s and s != "0" and s != "False"
    return s


def transform_extra_context(context1: dict, context2: dict | None) -> dict:
    if context2:
        for key, value in context2.items():
            context1[key] = value() if callable(value) else value
    return context1


def save(obj: Any, request: Any, view_type: str, param: dict | None = None) -> None:
    if hasattr(obj, "save_from_request"):
        obj.save_from_request(request, view_type, param)
    else:
        obj.save()
