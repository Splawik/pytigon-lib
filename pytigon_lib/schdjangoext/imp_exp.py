"""Export and import helpers for Django querysets.

The module serializes a queryset (including nested related objects) into plain
Python/JSON structures and restores those structures as model instances again.
It is intended for moving data between Pytigon/Django applications, for example
during backups, migrations or fixtures generation.

Reverse foreign-key and one-to-one relations are exported recursively. Reverse
many-to-many relations are not exported, because forward many-to-many fields
are already represented by their primary keys. Objects that are reached more
than once in a cyclic relation graph are exported as lightweight references
and skipped during import.

JSON export uses :class:`django.core.serializers.json.DjangoJSONEncoder`, so
values such as dates, decimals and UUIDs are preserved.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from django.apps import apps
from django.core import serializers
from django.core.exceptions import FieldDoesNotExist, ObjectDoesNotExist
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Field, Model, QuerySet

logger = logging.getLogger(__name__)

_REFERENCE_KEY = "reference"


def _relation_accessors(model_class: type[Model]) -> list[str]:
    """Return accessor names of reverse relations that are exported."""
    return [
        rel.get_accessor_name()
        for rel in model_class._meta.related_objects
        if not rel.many_to_many and not rel.parent_link and not rel.hidden
    ]


def _export_queryset(queryset: QuerySet, visited: set[tuple[str, Any]]) -> list[dict[str, Any]]:
    """Export every object in ``queryset``, sharing the ``visited`` registry."""
    accessors = _relation_accessors(queryset.model)
    if accessors:
        queryset = queryset.prefetch_related(*accessors)
    return [_export_object(obj, visited) for obj in queryset.iterator(chunk_size=200)]


def _export_object(obj: Model, visited: set[tuple[str, Any]]) -> dict[str, Any]:
    """Export one object together with the reverse relations it owns."""
    model_class = type(obj)
    key = (obj._meta.label_lower, obj.pk)
    if key in visited:
        return {
            "model": obj._meta.label_lower,
            "pk": obj.pk,
            "fields": {},
            _REFERENCE_KEY: True,
        }

    visited.add(key)
    (data,) = serializers.serialize("python", [obj])
    fields: dict[str, Any] = data["fields"]

    for rel in model_class._meta.related_objects:
        if rel.many_to_many or rel.parent_link or rel.hidden:
            continue
        accessor_name = rel.get_accessor_name()
        if rel.one_to_one:
            try:
                related_obj = getattr(obj, accessor_name)
            except ObjectDoesNotExist:
                fields[accessor_name] = None
            else:
                fields[accessor_name] = _export_object(related_obj, visited)
        else:
            fields[accessor_name] = _export_queryset(getattr(obj, accessor_name).all(), visited)

    return data


def export_django_queryset(queryset: QuerySet) -> list[dict[str, Any]]:
    """Serialize a queryset into a list of nested dictionaries.

    Each object is serialized with Django's Python serializer. Related objects
    reachable through reverse foreign-key and one-to-one relations are exported
    recursively and stored under the corresponding accessor key in the object's
    ``fields``. Objects already present in a cyclic relation graph are exported
    as references (marked with ``"reference": True``) instead of being visited
    again.

    Args:
        queryset: A Django ``QuerySet`` (or manager) to export.

    Returns:
        list[dict[str, Any]]: One dictionary per object, containing the model
        label, primary key and field values, with nested lists or dictionaries
        for related objects.
    """
    return _export_queryset(queryset, set())


def export_django_queryset2json(queryset: QuerySet) -> str:
    """Serialize a queryset and return the result as a JSON string.

    The export runs inside a database transaction to provide a consistent
    snapshot of the exported data. Django-aware JSON encoding is used, so
    dates, times, decimals and UUIDs can be serialized.

    Args:
        queryset: A Django ``QuerySet`` (or manager) to export.

    Returns:
        str: JSON representation of the exported object tree.
    """
    with transaction.atomic():
        object_list = export_django_queryset(queryset)
        return json.dumps(object_list, cls=DjangoJSONEncoder, indent=4, ensure_ascii=False)


def _resolve_parent_field(model_class: type[Model], parent: Model | int | str) -> Field:
    """Find the relation field that should point at ``parent``."""
    if isinstance(parent, Model):
        candidates = [
            field
            for field in model_class._meta.concrete_fields
            if field.is_relation and field.related_model is not None and isinstance(parent, field.related_model)
        ]
        for field in candidates:
            if field.name == "parent":
                return field
        if len(candidates) == 1:
            return candidates[0]
        if not candidates:
            raise ValueError(f"{model_class._meta.label} has no relation to {type(parent)._meta.label}")
        names = ", ".join(sorted(field.name for field in candidates))
        raise ValueError(
            f"Ambiguous relation between {model_class._meta.label} and {type(parent)._meta.label}; candidates: {names}"
        )

    try:
        field = model_class._meta.get_field("parent")
    except FieldDoesNotExist as exc:
        raise ValueError(f"{model_class._meta.label} has no 'parent' field to attach pk {parent!r}") from exc
    if not field.is_relation:
        raise ValueError(f"{model_class._meta.label}.parent is not a relation field")
    return field


def _get_parent_field(
    model_class: type[Model],
    parent: Model | int | str | None,
    parent_field_name: str | None,
) -> Field | None:
    """Resolve the parent relation field for an imported object."""
    if parent is None:
        return None
    if parent_field_name is None:
        return _resolve_parent_field(model_class, parent)
    try:
        return model_class._meta.get_field(parent_field_name)
    except FieldDoesNotExist as exc:
        raise ValueError(f"{model_class._meta.label} has no field {parent_field_name!r}") from exc


def _import_objects(
    data: list[dict[str, Any]] | dict[str, Any],
    upgrade: bool,
    parent: Model | int | str | None,
    parent_field_name: str | None,
    deferred_m2m: list[tuple[Model, str, list[Any]]],
) -> None:
    """Import serialized objects, collecting many-to-many operations."""
    if isinstance(data, dict):
        data = [data]

    saved_instances = []

    for obj in data:
        if obj.get(_REFERENCE_KEY):
            continue

        model_label = obj["model"]
        app_label, model_name = model_label.split(".", 1)
        model_class = apps.get_model(app_label, model_name)
        parent_field = _get_parent_field(model_class, parent, parent_field_name)

        concrete_fields = {field.name: field for field in model_class._meta.concrete_fields}
        m2m_names = {field.name for field in model_class._meta.many_to_many}
        reverse_relations = {
            rel.get_accessor_name(): rel
            for rel in model_class._meta.related_objects
            if not rel.many_to_many and not rel.parent_link and not rel.hidden
        }
        reverse_m2m = {
            rel.get_accessor_name() for rel in model_class._meta.related_objects if rel.many_to_many and not rel.hidden
        }

        fields: dict[str, Any] = {}
        children: list[tuple[Any, Any]] = []
        m2m_values: dict[str, list[Any]] = {}

        for key, value in obj.get("fields", {}).items():
            if key in reverse_relations:
                children.append((reverse_relations[key], value))
            elif key in m2m_names:
                m2m_values[key] = value or []
            elif key in concrete_fields:
                field = concrete_fields[key]
                if parent_field is not None and field.name == parent_field.name:
                    continue
                fields[field.attname] = value
            elif key in reverse_m2m:
                logger.warning(
                    "Skipping reverse many-to-many field %r on %s during import",
                    key,
                    model_class._meta.label,
                )
            else:
                raise ValueError(f"Unknown field {key!r} for model {model_class._meta.label}")

        try:
            instance = model_class(**fields)
        except Exception as exc:
            raise ValueError(f"Cannot create {model_class._meta.label} from fields {sorted(fields)}: {exc}") from exc

        if parent is not None:
            if isinstance(parent, Model):
                setattr(instance, parent_field.name, parent)
            else:
                setattr(instance, parent_field.attname, parent)

        if upgrade:
            pk = obj.get("pk")
            if pk is not None:
                lookup: dict[str, Any] = {"pk": pk}
                if parent is not None:
                    lookup[parent_field.name] = parent
                existing = model_class._default_manager.filter(**lookup).first()
                if existing is not None:
                    instance.pk = existing.pk
                    instance._state.adding = False

        try:
            instance.save()
            saved_instances.append(instance)
        except Exception as exc:
            raise ValueError(f"Cannot save {model_class._meta.label} (pk={instance.pk}): {exc}") from exc

        for name, pks in m2m_values.items():
            deferred_m2m.append((instance, name, pks))

        for rel, child_data in children:
            if child_data is None:
                continue
            _import_objects(child_data, upgrade, instance, rel.field.name, deferred_m2m)
    return saved_instances


def _apply_m2m(deferred_m2m: list[tuple[Model, str, list[Any]]]) -> None:
    """Attach deferred many-to-many values once all objects exist."""
    for instance, name, pks in deferred_m2m:
        manager = getattr(instance, name)
        if pks:
            related_model = manager.model
            existing_pks = set(related_model._default_manager.filter(pk__in=pks).values_list("pk", flat=True))
            missing_pks = [pk for pk in pks if pk not in existing_pks]
            if missing_pks:
                logger.warning(
                    "Missing %s rows for %s.%s many-to-many relation: %s",
                    related_model._meta.label,
                    instance._meta.label,
                    name,
                    missing_pks,
                )
            values = list(existing_pks)
        else:
            values = []

        try:
            manager.set(values)
        except Exception as exc:
            raise ValueError(
                f"Cannot set many-to-many field {name!r} on {instance._meta.label} (pk={instance.pk}): {exc}"
            ) from exc


def import_django_objects(
    data: list[dict[str, Any]] | dict[str, Any],
    upgrade: bool = False,
    parent: Model | int | str | None = None,
    *,
    _parent_field: str | None = None,
) -> None:
    """Import a nested data structure produced by :func:`export_django_queryset`.

    Objects are recreated for the model indicated by the ``model`` key (in
    ``app_label.model_name`` form). Nested child collections and reverse
    one-to-one objects are imported recursively and attached to the saved
    parent through the relation field discovered from the model metadata.
    Reference markers produced for cyclic relations are skipped. Forward
    many-to-many fields are restored after all objects have been saved, using
    the primary keys stored in the export.

    The whole import runs inside a single database transaction, so any error
    rolls back all changes.

    Args:
        data: Serialized objects, as returned by
            :func:`export_django_queryset`. A single dictionary is accepted as
            well.
        upgrade: When ``True``, try to match an existing object by primary key
            (optionally filtered by ``parent``) and reuse its primary key
            instead of always inserting a new row.
        parent: Optional parent instance (or primary key) assigned to the
            imported objects.
        _parent_field: Internal name of the relation field that points at
            ``parent``; resolved automatically when omitted.

    Returns:
        None

    Raises:
        ValueError: If the serialized model, a field or a relation cannot be
            resolved, or if saving an object fails.
    """
    with transaction.atomic():
        deferred_m2m: list[tuple[Model, str, list[Any]]] = []
        saved_instances = _import_objects(data, upgrade, parent or None, _parent_field, deferred_m2m)
        _apply_m2m(deferred_m2m)
    return saved_instances


def import_django_objects_json(
    json_data: str,
    upgrade: bool = False,
    parent: Model | int | str | None = None,
) -> None:
    """Import objects from JSON produced by :func:`export_django_queryset2json`.

    The JSON payload is parsed and then imported with
    :func:`import_django_objects`, which runs the whole import inside a single
    database transaction. A failure rolls back the entire import.

    Args:
        json_data: JSON string containing the serialized object tree.
        upgrade: Forwarded to :func:`import_django_objects`; when ``True``,
            existing objects matched by primary key are updated.
        parent: Optional parent instance (or primary key) assigned to the
            imported objects.

    Returns:
        None

    Raises:
        ValueError: If the payload cannot be parsed or any object cannot be
            imported.
    """
    data = json.loads(json_data)
    saved_instances = import_django_objects(data, upgrade, parent)
    return saved_instances
