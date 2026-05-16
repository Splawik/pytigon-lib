"""Extended JSON encoding/decoding with support for datetime, Decimal, and numpy types.

Provides URL-safe encoding (via ``dumps``/``loads``) and plain JSON
helpers (``json_dumps``/``json_loads``).
"""

import datetime
import json
from decimal import Decimal
from urllib.parse import quote_plus, unquote_plus

# Types that JSONEncoder handles natively – we only intervene for others.
_STANDARD_TYPES = frozenset(
    {
        "list",
        "unicode",
        "str",
        "int",
        "long",
        "float",
        "bool",
        "NoneType",
    }
)

# Restricted builtins and allowed types for safe ``eval()`` in ``as_complex``.
# Only types that the encoder may produce via ``repr()`` are permitted.
_SAFE_EVAL_GLOBALS = {
    "__builtins__": {
        "True": True,
        "False": False,
        "None": None,
        "int": int,
        "float": float,
        "str": str,
        "list": list,
        "dict": dict,
        "tuple": tuple,
    },
    "datetime": datetime,
    "Decimal": Decimal,
}


class ComplexEncoder(json.JSONEncoder):
    """JSON encoder that handles datetime, Decimal, numpy arrays, and other
    non-standard types by serializing their ``repr()`` as a special
    ``{"object": "..."}`` envelope.
    """

    def default(self, obj):
        """Encode a non-standard Python object.

        Args:
            obj: The object to encode.

        Returns:
            A JSON-serializable representation (a dict with an ``"object"``
            key for complex types, or a list for numpy arrays).
        """
        type_name = obj.__class__.__name__
        if type_name not in _STANDARD_TYPES:
            if isinstance(obj, datetime.datetime):
                return {"object": repr(obj).replace(", tzinfo=<UTC>", "")}
            if isinstance(obj, datetime.date):
                return {"object": repr(obj)}
            if isinstance(obj, Decimal):
                return {"object": repr(obj)}
            if hasattr(obj, "tolist"):
                return obj.tolist()
            return {"object": repr(obj)}
        return super().default(obj)


def as_complex(dct):
    """Convert ``{"object": "..."}`` JSON envelopes back to Python objects.

    Uses ``eval()`` with a restricted globals dict that only allows
    :mod:`datetime`, :class:`~decimal.Decimal`, and safe builtins.
    Falls back to returning ``None`` if evaluation fails.

    Args:
        dct: A dictionary from JSON decoding.

    Returns:
        The original Python object, or *dct* unchanged if it has no
        ``"object"`` key, or ``None`` if evaluation of the key fails.
    """
    if "object" in dct:
        try:
            return eval(dct["object"], _SAFE_EVAL_GLOBALS)
        except Exception:
            return None
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
