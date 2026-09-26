"""Optional PyArrow based streaming export/import helpers.

The helpers operate on Django querysets and plain row iterables. Django is not
imported here: models and querysets are duck typed through their public API
(``model._meta.fields``, ``queryset.values_list(...)`` and
``model._default_manager.bulk_create``).

PyArrow is imported lazily. When it is not installed the module keeps working
through a standard library fallback:

* :func:`stream_rows`, :func:`export_queryset` and :func:`import_to_model`
  support CSV without PyArrow.
* Parquet / Arrow IPC targets transparently fall back to CSV (a warning is
  logged and the returned name points at the ``.csv`` file).
* Arrow-only entry points (:func:`queryset_to_arrow`, :func:`read_table`, ...)
  raise :class:`ArrowNotAvailable` with a clear message.
"""

import csv
import io
import json
import logging
import os
from datetime import date, datetime, time
from decimal import Decimal

logger = logging.getLogger(__name__)

PARQUET_FORMATS = frozenset({"parquet", "pq"})
IPC_FORMATS = frozenset({"arrow", "ipc", "feather"})
CSV_FORMATS = frozenset({"csv", "txt"})

_INT_TYPES = frozenset(
    {
        "AutoField",
        "BigAutoField",
        "SmallAutoField",
        "IntegerField",
        "BigIntegerField",
        "SmallIntegerField",
        "PositiveIntegerField",
        "PositiveSmallIntegerField",
        "PositiveBigIntegerField",
    }
)
_FLOAT_TYPES = frozenset({"FloatField"})
_TEXT_TYPES = frozenset({"CharField", "TextField", "SlugField", "EmailField", "URLField"})

_EXTENSION_FORMATS = {
    ".parquet": "parquet",
    ".pq": "parquet",
    ".arrow": "arrow",
    ".ipc": "arrow",
    ".feather": "arrow",
    ".csv": "csv",
    ".txt": "csv",
}

CONTENT_TYPES = {
    "parquet": "application/vnd.apache.parquet",
    "arrow": "application/vnd.apache.arrow.stream",
    "csv": "text/csv",
}

__all__ = [
    "CONTENT_TYPES",
    "ArrowNotAvailable",
    "arrow_to_ipc_bytes",
    "arrow_to_parquet_bytes",
    "data_to_arrow",
    "django_field_to_arrow_type",
    "export_queryset",
    "export_queryset_to_bytes",
    "format_from_name",
    "has_arrow",
    "import_to_model",
    "iter_rows",
    "model_arrow_schema",
    "pyarrow_module",
    "queryset_to_arrow",
    "read_rows",
    "read_table",
    "resolve_fields",
    "stream_rows",
]


class ArrowNotAvailable(RuntimeError):
    """Raised when a PyArrow-only operation is requested without PyArrow."""


_PYARROW = None
_PYARROW_CHECKED = False


def pyarrow_module():
    """Return the imported ``pyarrow`` module, or ``None`` when unavailable."""
    global _PYARROW, _PYARROW_CHECKED
    if not _PYARROW_CHECKED:
        _PYARROW_CHECKED = True
        try:
            import pyarrow
        except Exception:
            _PYARROW = None
        else:
            _PYARROW = pyarrow
    return _PYARROW


def has_arrow():
    """Return ``True`` when PyArrow is importable."""
    return pyarrow_module() is not None


def _require_arrow():
    pa = pyarrow_module()
    if pa is None:
        raise ArrowNotAvailable("PyArrow is not installed; use stream_rows() or export_queryset(format='csv') instead.")
    return pa


def _pyarrow_parquet():
    import pyarrow.parquet as parquet

    return parquet


def _pyarrow_csv():
    import pyarrow.csv as csv_module

    return csv_module


def format_from_name(name):
    """Infer an export format from a file name or extension."""
    if not name:
        return None
    extension = os.path.splitext(str(name))[1].lower()
    return _EXTENSION_FORMATS.get(extension)


def model_fields(model):
    """Return the concrete fields of a Django model (empty for non-models)."""
    meta = getattr(model, "_meta", None)
    return list(getattr(meta, "fields", ()) or ())


def resolve_fields(model, fields=None):
    """Resolve field names into ``(name, field)`` pairs.

    ``None`` selects all model fields. Unknown names are ignored so that a
    caller can pass a superset of names safely.
    """
    all_fields = model_fields(model)
    by_name = {}
    for field in all_fields:
        by_name[field.name] = field
        attname = getattr(field, "attname", None)
        if attname:
            by_name.setdefault(attname, field)
    if fields is None:
        return [(field.name, field) for field in all_fields]
    resolved = []
    for name in fields:
        field = by_name.get(name)
        if field is not None:
            resolved.append((name, field))
    return resolved


def django_field_to_arrow_type(field):
    """Map a Django model field to a PyArrow data type."""
    pa = _require_arrow()
    internal = field.get_internal_type()
    if internal in ("ForeignKey", "OneToOneField"):
        target = getattr(field, "target_field", None)
        if target is not None:
            return django_field_to_arrow_type(target)
        return pa.int64()
    if internal == "DecimalField":
        max_digits = int(getattr(field, "max_digits", None) or 38)
        decimal_places = int(getattr(field, "decimal_places", None) or 0)
        return pa.decimal128(max_digits, min(decimal_places, max_digits))
    if internal == "DateTimeField":
        return pa.timestamp("us")
    if internal == "TimeField":
        return pa.time64("us")
    if internal == "DurationField":
        return pa.duration("us")
    if internal == "DateField":
        return pa.date32()
    if internal == "BooleanField":
        return pa.bool_()
    if internal == "BinaryField":
        return pa.binary()
    if internal in _FLOAT_TYPES:
        return pa.float64()
    if internal in _INT_TYPES:
        return pa.int64()
    return pa.string()


def model_arrow_schema(model, fields=None):
    """Build a PyArrow schema for *model* following the field ordering."""
    pa = _require_arrow()
    return pa.schema([(name, django_field_to_arrow_type(field)) for name, field in resolve_fields(model, fields)])


def _resolved_internal_types(resolved):
    internal_types = {}
    for name, field in resolved:
        internal = field.get_internal_type()
        if internal in ("ForeignKey", "OneToOneField"):
            target = getattr(field, "target_field", None)
            internal = target.get_internal_type() if target is not None else "IntegerField"
        internal_types[name] = internal
    return internal_types


def _convert_value(internal, value):
    if value is None:
        return None
    if internal == "JSONField":
        return value if isinstance(value, str) else json.dumps(value, default=str)
    if internal in ("UUIDField", "GenericIPAddressField", "IPAddressField"):
        return str(value)
    return value


def _csv_value(value):
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return str(value)


def _coerce_for_field(field, value):
    """Coerce a CSV string value to the Python type of a model field.

    Values coming from Parquet/Arrow are already typed and pass through
    unchanged. Best effort: unparsable values are returned as-is.
    """
    internal = field.get_internal_type()
    if internal in ("ForeignKey", "OneToOneField"):
        target = getattr(field, "target_field", None)
        internal = target.get_internal_type() if target is not None else "IntegerField"
    if value is None:
        return None
    if value == "":
        return "" if internal in _TEXT_TYPES else None
    try:
        if internal in _INT_TYPES:
            return int(value)
        if internal in _FLOAT_TYPES:
            return float(value)
        if internal == "DecimalField":
            return value if isinstance(value, Decimal) else Decimal(str(value))
        if internal == "BooleanField":
            if isinstance(value, bool):
                return value
            return str(value).strip().lower() in ("1", "true", "t", "yes", "y", "on")
        if internal == "DateField":
            if isinstance(value, datetime):
                return value.date()
            if isinstance(value, date):
                return value
            return date.fromisoformat(str(value)[:10])
        if internal == "DateTimeField":
            return value if isinstance(value, datetime) else datetime.fromisoformat(str(value))
        if internal == "TimeField":
            return value if isinstance(value, time) else time.fromisoformat(str(value))
        if internal == "JSONField" and not isinstance(value, (dict, list)):
            return json.loads(value)
    except (TypeError, ValueError):
        logger.warning("Cannot coerce %r to %s; keeping the raw value", value, internal)
        return value
    return value


def _target_name(target):
    if isinstance(target, (str, os.PathLike)):
        return os.fspath(target)
    return getattr(target, "name", None)


def _csv_path(target):
    if isinstance(target, (str, os.PathLike)):
        base, _ = os.path.splitext(os.fspath(target))
        return base + ".csv"
    return target


def _open_text_target(target):
    if hasattr(target, "write") and not isinstance(target, (str, os.PathLike)):
        return target, False
    path = os.fspath(target)
    return open(path, "w", newline="", encoding="utf-8"), True


def _open_binary_target(target):
    if hasattr(target, "write") and not isinstance(target, (str, os.PathLike)):
        return target, False
    path = os.fspath(target)
    return open(path, "wb"), True


def _open_text_read(source):
    if hasattr(source, "read") and not isinstance(source, (str, os.PathLike)):
        return source, False
    path = os.fspath(source)
    return open(path, newline="", encoding="utf-8"), True


def stream_rows(source, fields=None, chunk_size=10000):
    """Yield rows as tuples without materialising the whole source.

    Works with Django querysets (streamed through
    ``values_list(...).iterator(chunk_size=...)``) and with any iterable of
    rows.
    """
    if hasattr(source, "values_list"):
        values = source.values_list(*fields) if fields else source.values_list()
        if hasattr(values, "iterator"):
            yield from values.iterator(chunk_size=chunk_size)
        else:
            yield from values
        return
    for row in source:
        yield tuple(row.values()) if isinstance(row, dict) else tuple(row)


def _iter_records(source, names, internal_types, chunk_size):
    for row in stream_rows(source, names, chunk_size):
        yield {name: _convert_value(internal_types.get(name), value) for name, value in zip(names, row)}


def _record_chunks(source, names, internal_types, chunk_size):
    buffer = []
    for record in _iter_records(source, names, internal_types, chunk_size):
        buffer.append(record)
        if len(buffer) >= chunk_size:
            yield buffer
            buffer = []
    if buffer:
        yield buffer


def queryset_to_arrow(queryset, fields=None, chunk_size=10000, schema=None):
    """Build a PyArrow table from *queryset* using bounded chunks.

    Chunks are appended to an Arrow table as they are produced, so only one
    batch of Python objects exists at a time. Raises
    :class:`ArrowNotAvailable` when PyArrow is not installed.
    """
    pa = _require_arrow()
    model = getattr(queryset, "model", None)
    resolved = resolve_fields(model, fields) if model is not None else []
    names = [name for name, _ in resolved] if resolved else list(fields or [])
    if not names:
        raise ValueError("Unable to determine columns; pass 'fields' explicitly")

    if schema is None and model is not None:
        schema = model_arrow_schema(model, fields)
    internal_types = _resolved_internal_types(resolved)

    tables = []
    for records in _record_chunks(queryset, names, internal_types, chunk_size):
        tables.append(pa.Table.from_pylist(records, schema=schema))
    if not tables:
        return schema.empty_table() if schema is not None else pa.table({})
    return pa.concat_tables(tables)


def _export_parquet(source, target, names, internal_types, chunk_size, schema, options):
    pa = pyarrow_module()
    sink, should_close = _open_binary_target(target)
    try:
        writer = None
        try:
            for records in _record_chunks(source, names, internal_types, chunk_size):
                table = pa.Table.from_pylist(records, schema=schema)
                if writer is None:
                    schema = schema or table.schema
                    writer = _pyarrow_parquet().ParquetWriter(sink, schema, **options)
                writer.write_table(table)
            if writer is None:
                schema = schema or pa.schema([(name, pa.string()) for name in names])
                writer = _pyarrow_parquet().ParquetWriter(sink, schema, **options)
        finally:
            if writer is not None:
                writer.close()
    finally:
        if should_close:
            sink.close()
    return _target_name(target)


def _export_ipc(source, target, names, internal_types, chunk_size, schema):
    pa = pyarrow_module()
    sink, should_close = _open_binary_target(target)
    try:
        writer = None
        try:
            for records in _record_chunks(source, names, internal_types, chunk_size):
                table = pa.Table.from_pylist(records, schema=schema)
                if writer is None:
                    schema = schema or table.schema
                    writer = pa.ipc.new_stream(sink, schema)
                writer.write_table(table)
            if writer is None:
                schema = schema or pa.schema([(name, pa.string()) for name in names])
                writer = pa.ipc.new_stream(sink, schema)
        finally:
            if writer is not None:
                writer.close()
    finally:
        if should_close:
            sink.close()
    return _target_name(target)


def _export_csv(source, target, names, chunk_size, internal_types=None):
    sink, should_close = _open_text_target(target)
    try:
        writer = csv.writer(sink)
        writer.writerow(names)
        for row in stream_rows(source, names, chunk_size):
            if internal_types:
                writer.writerow(
                    [_csv_value(_convert_value(internal_types.get(name), value)) for name, value in zip(names, row)]
                )
            else:
                writer.writerow([_csv_value(value) for value in row])
    finally:
        if should_close:
            sink.close()
    return _target_name(target)


def export_queryset(
    queryset,
    target,
    fields=None,
    format=None,
    chunk_size=10000,
    schema=None,
    **writer_options,
):
    """Stream *queryset* to a file, path or file-like object.

    ``format`` is inferred from the target name when omitted. Parquet and
    Arrow IPC require PyArrow; without it the data is written as CSV instead
    and the actual output name is returned.
    """
    fmt = (format or format_from_name(_target_name(target)) or "parquet").lower()
    model = getattr(queryset, "model", None)
    resolved = resolve_fields(model, fields) if model is not None else []
    names = [name for name, _ in resolved] if resolved else list(fields or [])
    if not names:
        raise ValueError("Unable to determine columns; pass 'fields' explicitly")

    internal_types = _resolved_internal_types(resolved)

    if fmt in PARQUET_FORMATS or fmt in IPC_FORMATS:
        if not has_arrow():
            logger.warning(
                "PyArrow is not installed; exporting %r as CSV instead",
                _target_name(target),
            )
            return _export_csv(queryset, _csv_path(target), names, chunk_size, internal_types)
        if schema is None and model is not None:
            schema = model_arrow_schema(model, fields)
        if fmt in PARQUET_FORMATS:
            return _export_parquet(queryset, target, names, internal_types, chunk_size, schema, writer_options)
        return _export_ipc(queryset, target, names, internal_types, chunk_size, schema)

    if fmt in CSV_FORMATS:
        return _export_csv(queryset, target, names, chunk_size, internal_types)

    raise ValueError(f"Unsupported export format: {fmt!r}")


def export_queryset_to_bytes(queryset, format="parquet", fields=None, chunk_size=10000, **writer_options):
    """Return ``(content, content_type, extension)`` for a queryset export.

    Falls back to CSV when PyArrow is missing, so a view can always stream a
    download.
    """
    fmt = (format or "parquet").lower()
    if fmt in CSV_FORMATS or not has_arrow():
        buffer = io.StringIO()
        export_queryset(queryset, buffer, fields=fields, format="csv", chunk_size=chunk_size)
        return buffer.getvalue().encode("utf-8"), CONTENT_TYPES["csv"], "csv"

    buffer = io.BytesIO()
    export_queryset(
        queryset,
        buffer,
        fields=fields,
        format=fmt,
        chunk_size=chunk_size,
        **writer_options,
    )
    extension = "parquet" if fmt in PARQUET_FORMATS else "arrow"
    content_type = CONTENT_TYPES["parquet"] if fmt in PARQUET_FORMATS else CONTENT_TYPES["arrow"]
    return buffer.getvalue(), content_type, extension


def data_to_arrow(data):
    """Convert a JSON-like dict or list of dicts into a PyArrow table.

    Returns ``None`` when PyArrow is not installed.
    """
    pa = pyarrow_module()
    if pa is None:
        return None
    if isinstance(data, dict):
        return pa.Table.from_pylist([data])
    if isinstance(data, (list, tuple)):
        items = list(data)
        if not items:
            return pa.table({})
        if isinstance(items[0], dict):
            return pa.Table.from_pylist(items)
    raise TypeError("data_to_arrow expects a dict or a list of dicts")


def arrow_to_parquet_bytes(table, **options):
    """Serialize a PyArrow table to Parquet bytes."""
    buffer = io.BytesIO()
    _pyarrow_parquet().write_table(table, buffer, **options)
    return buffer.getvalue()


def arrow_to_ipc_bytes(table):
    """Serialize a PyArrow table to Arrow IPC stream bytes."""
    pa = _require_arrow()
    buffer = io.BytesIO()
    writer = pa.ipc.new_stream(buffer, table.schema)
    try:
        writer.write_table(table)
    finally:
        writer.close()
    return buffer.getvalue()


def read_table(source, format=None):
    """Read a Parquet/Arrow/CSV file into a PyArrow table."""
    pa = pyarrow_module()
    if pa is None:
        raise ArrowNotAvailable("PyArrow is not installed")
    fmt = (format or format_from_name(_target_name(source)) or "parquet").lower()
    if fmt in PARQUET_FORMATS:
        return _pyarrow_parquet().read_table(source)
    if fmt in IPC_FORMATS:
        if hasattr(source, "read") and not isinstance(source, (str, os.PathLike)):
            return pa.ipc.open_stream(source).read_all()
        with open(os.fspath(source), "rb") as handle:
            return pa.ipc.open_stream(handle).read_all()
    if fmt in CSV_FORMATS:
        return _pyarrow_csv().read_csv(source)
    raise ValueError(f"Unsupported read format: {fmt!r}")


def _iter_csv_rows(source, columns):
    sink, should_close = _open_text_read(source)
    try:
        reader = csv.reader(sink)
        header = next(reader, None)
        if header is None:
            return
        if columns:
            indexes = [header.index(name) for name in columns]
            for row in reader:
                yield tuple(row[index] for index in indexes)
        else:
            for row in reader:
                yield tuple(row)
    finally:
        if should_close:
            sink.close()


def iter_rows(source, format=None, columns=None, batch_size=1000):
    """Yield rows as tuples, streaming in batches when PyArrow is available."""
    fmt = (format or format_from_name(_target_name(source)) or "csv").lower()
    if fmt in CSV_FORMATS:
        yield from _iter_csv_rows(source, columns)
        return
    if not has_arrow():
        raise ArrowNotAvailable(f"PyArrow is required to read {fmt!r} files; use CSV instead.")
    table = read_table(source, fmt)
    names = list(columns) if columns else table.column_names
    for batch in table.to_batches(max_chunksize=batch_size):
        arrays = [batch.column(batch.schema.get_field_index(name)) for name in names]
        for index in range(batch.num_rows):
            yield tuple(array[index].as_py() for array in arrays)


def read_rows(source, format=None, columns=None):
    """Return all rows of *source* as a list of tuples."""
    return list(iter_rows(source, format=format, columns=columns))


def import_to_model(source, model, fields=None, batch_size=1000, format=None, field_map=None):
    """Import rows from Parquet/Arrow/CSV into *model* using ``bulk_create``.

    ``field_map`` maps source column names to model field names. Without it the
    source columns must share names with the model fields. Returns the number of
    created objects.
    """
    fmt = (format or format_from_name(_target_name(source)) or "csv").lower()
    if field_map:
        source_columns = list(field_map.keys())
        target_names = [field_map[name] for name in source_columns]
    else:
        if fields is None:
            fields = [field.name for field in model_fields(model)]
        source_columns = list(fields)
        target_names = list(fields)

    manager = getattr(model, "_default_manager", None) or getattr(model, "objects", None)
    if manager is None:
        raise TypeError("model must provide '_default_manager' or 'objects'")
    field_by_name = {name: field for name, field in resolve_fields(model, target_names)}
    total = 0
    batch = []
    for row in iter_rows(source, format=fmt, columns=source_columns, batch_size=batch_size):
        values = {}
        for attr, value in zip(target_names, row):
            field = field_by_name.get(attr)
            values[attr] = _coerce_for_field(field, value) if field is not None else value
        batch.append(model(**values))
        if len(batch) >= batch_size:
            manager.bulk_create(batch, batch_size=batch_size)
            total += len(batch)
            batch = []
    if batch:
        manager.bulk_create(batch, batch_size=batch_size)
        total += len(batch)
    return total
