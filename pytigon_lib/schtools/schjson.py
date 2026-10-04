"""Extended JSON encoding/decoding with support for datetime, Decimal, and numpy types.

Provides URL-safe encoding (via ``dumps``/``loads``) and plain JSON
helpers (``json_dumps``/``json_loads``).

Non-standard values travel in a *typed envelope*::

    {"__pytigon_type__": "datetime", "value": "2023-01-01T12:30:45"}
    {"__pytigon_type__": "date",     "value": "2023-01-01"}
    {"__pytigon_type__": "decimal",  "value": "10.5"}

Decoding **never evaluates Python source**. An earlier version accepted a
``{"object": "<repr>"}`` envelope and ran it through ``eval()``; that made every
decoded JSON payload a code-execution primitive, because
``globals()["__builtins__"]`` escaped the validator and reached ``os.system``.
The legacy envelope is still *read* for compatibility with data already stored
in databases, but it is parsed structurally: only exact
``datetime``/``date``/``time``/``timedelta`` constructions with literal numeric
arguments, ``Decimal`` with a literal argument, and plain Python literals are
reconstructed. Anything else is returned as ``None`` (for the legacy envelope)
or left untouched (for a malformed typed envelope).
"""

import ast
import datetime
import json
from decimal import Decimal, InvalidOperation
from urllib.parse import quote_plus, unquote_plus

# Types that JSONEncoder handles natively – we only intervene for others.
_STANDARD_TYPES = frozenset(
    {
        "list",
        "str",
        "int",
        "float",
        "bool",
        "NoneType",
    }
)

# Keys of the typed envelope written by :class:`ComplexEncoder`.
_ENVELOPE_TYPE_KEY = "__pytigon_type__"
_ENVELOPE_VALUE_KEY = "value"

# Key of the historical, eval-based envelope that is still read for
# backward compatibility with data stored by older releases.
_LEGACY_OBJECT_KEY = "object"

# Constructors that the legacy ``repr()`` parser is allowed to rebuild. Each
# takes literal arguments only and cannot execute code.
_LEGACY_CONSTRUCTORS = {
    "datetime.datetime": datetime.datetime,
    "datetime.date": datetime.date,
    "datetime.time": datetime.time,
    "datetime.timedelta": datetime.timedelta,
}


class _Missing:
    """Sentinel meaning "not a recognised legacy envelope"."""

    __slots__ = ()

    def __repr__(self):  # pragma: no cover - debugging aid
        return "<missing>"


_MISSING = _Missing()


class ComplexEncoder(json.JSONEncoder):
    """JSON encoder for datetime, Decimal, numpy arrays and other types.

    ``datetime``/``date``/``Decimal`` are written as typed envelopes so that
    decoding needs no ``eval()``. Arrays exposing ``tolist()`` are written as
    JSON arrays. Any remaining object falls back to its ``repr()`` in an
    informational ``{"object": "..."}`` envelope that is not reconstructed.
    """

    def default(self, obj):
        """Encode a non-standard Python object.

        Args:
            obj: The object to encode.

        Returns:
            A JSON-serializable representation.
        """
        type_name = obj.__class__.__name__
        if type_name not in _STANDARD_TYPES:
            if isinstance(obj, datetime.datetime):
                return {
                    _ENVELOPE_TYPE_KEY: "datetime",
                    _ENVELOPE_VALUE_KEY: obj.isoformat(),
                }
            if isinstance(obj, datetime.date):
                return {
                    _ENVELOPE_TYPE_KEY: "date",
                    _ENVELOPE_VALUE_KEY: obj.isoformat(),
                }
            if isinstance(obj, Decimal):
                return {
                    _ENVELOPE_TYPE_KEY: "decimal",
                    _ENVELOPE_VALUE_KEY: str(obj),
                }
            if hasattr(obj, "tolist"):
                return obj.tolist()
            return {_LEGACY_OBJECT_KEY: repr(obj)}
        return super().default(obj)


def _dotted_name(node):
    """Return ``a.b.c`` for an attribute chain rooted in a plain name, else None."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return None


def _literal_args(nodes):
    """Return the literal values of *nodes* or None if any is not a literal.

    Accepts ints, floats, strings, bools, ``None`` and unary ``+``/``-`` on
    numeric constants. Everything else (names, calls, subscripts, f-strings,
    comprehensions, …) makes the whole list non-literal.
    """
    values = []
    for node in nodes:
        if isinstance(node, ast.Constant):
            values.append(node.value)
        elif (
            isinstance(node, ast.UnaryOp)
            and isinstance(node.op, (ast.USub, ast.UAdd))
            and isinstance(node.operand, ast.Constant)
            and isinstance(node.operand.value, (int, float))
            and not isinstance(node.operand.value, bool)
        ):
            values.append(
                -node.operand.value if isinstance(node.op, ast.USub) else node.operand.value
            )
        else:
            return None
    return values


def _parse_legacy_object(value):
    """Rebuild a value from a legacy ``repr()`` envelope without executing code.

    Only these shapes are recognised:

    * ``datetime.datetime(...)`` / ``datetime.date(...)`` /
      ``datetime.time(...)`` / ``datetime.timedelta(...)`` with literal numeric
      arguments,
    * ``Decimal(<literal>)``,
    * plain Python literals (``42``, ``3.14``, ``"x"``, ``[1, 2]``, ``True`` …).

    Returns :data:`_MISSING` when the value is not one of them. Notably, calls,
    subscripting, attribute access on non-``datetime`` bases and free names are
    never evaluated.
    """
    if not isinstance(value, str):
        return _MISSING

    text = value.strip()
    if not text:
        return _MISSING

    try:
        node = ast.parse(text, mode="eval").body
    except (SyntaxError, ValueError):
        node = None

    if isinstance(node, ast.Call):
        name = _dotted_name(node.func)
        args = _literal_args(node.args)
        if args is not None and not node.keywords:
            if name in _LEGACY_CONSTRUCTORS:
                try:
                    return _LEGACY_CONSTRUCTORS[name](*args)
                except (TypeError, ValueError, OverflowError):
                    return _MISSING
            if name == "Decimal" and len(args) == 1:
                arg = args[0]
                if isinstance(arg, (int, float, str)) and not isinstance(arg, bool):
                    try:
                        return Decimal(str(arg))
                    except (InvalidOperation, ValueError, TypeError):
                        return _MISSING
                return _MISSING

    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        return _MISSING


def _decode_typed_envelope(dct):
    """Decode a typed envelope, or return *dct* unchanged when malformed."""
    type_name = dct.get(_ENVELOPE_TYPE_KEY)
    value = dct.get(_ENVELOPE_VALUE_KEY)

    if type_name == "datetime" and isinstance(value, str):
        try:
            return datetime.datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return dct
    if type_name == "date" and isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value)
        except (TypeError, ValueError):
            return dct
    if type_name == "decimal":
        if isinstance(value, (int, float, str)) and not isinstance(value, bool):
            try:
                return Decimal(str(value))
            except (InvalidOperation, ValueError, TypeError):
                return dct
        return dct
    return dct


def as_complex(dct):
    """Convert a JSON envelope back to a Python object, without evaluating code.

    Handles the typed envelope written by :class:`ComplexEncoder` and, for
    compatibility with previously stored data, the legacy
    ``{"object": "<repr>"}`` envelope, which is parsed structurally (see
    :func:`_parse_legacy_object`).

    Args:
        dct: A dictionary from JSON decoding.

    Returns:
        The reconstructed object, or *dct* unchanged when it carries no
        recognised envelope. A legacy ``{"object": ...}`` envelope whose value
        cannot be safely reconstructed yields ``None``.
    """
    if not isinstance(dct, dict):
        return dct
    if _ENVELOPE_TYPE_KEY in dct:
        return _decode_typed_envelope(dct)
    if _LEGACY_OBJECT_KEY in dct:
        parsed = _parse_legacy_object(dct[_LEGACY_OBJECT_KEY])
        return None if parsed is _MISSING else parsed
    return dct


def dumps(obj):
    """Encode an object to a URL-safe JSON string.

    Args:
        obj: The Python object to encode.

    Returns:
        A URL-encoded JSON string.

    Raises:
        ValueError: If encoding fails.
    """
    try:
        return quote_plus(json.dumps(obj, cls=ComplexEncoder))
    except (TypeError, ValueError) as e:
        raise ValueError(f"Failed to encode object: {e}")


def loads(json_str):
    """Decode a URL-encoded JSON string back to a Python object.

    Args:
        json_str: The URL-encoded JSON string.

    Returns:
        The decoded Python object.

    Raises:
        ValueError: If decoding fails.
    """
    try:
        return json.loads(unquote_plus(json_str), object_hook=as_complex)
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to decode JSON string: {e}")


def json_dumps(obj, indent=None):
    """Encode an object to a plain (non-URL-encoded) JSON string.

    Args:
        obj: The Python object to encode.
        indent: Optional indentation for pretty-printing.

    Returns:
        A JSON string.

    Raises:
        ValueError: If encoding fails.
    """
    try:
        return json.dumps(obj, cls=ComplexEncoder, indent=indent)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Failed to encode object: {e}")


def json_loads(json_str):
    """Decode a plain JSON string back to a Python object.

    Args:
        json_str: The JSON string.

    Returns:
        The decoded Python object.

    Raises:
        ValueError: If decoding fails.
    """
    try:
        return json.loads(json_str, object_hook=as_complex)
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to decode JSON string: {e}")


class ComplexDecoder(json.JSONDecoder):
    """JSON decoder that uses :func:`as_complex` to restore complex objects."""

    def decode(self, s):
        """Decode a JSON string.

        Args:
            s: The JSON string.

        Returns:
            The decoded Python object.
        """
        return json_loads(s)
