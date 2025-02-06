"""Helper class for JSON encoding and decoding."""

import json
from urllib.parse import quote_plus, unquote_plus
import datetime
from decimal import Decimal


class ComplexEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles complex types like datetime and Decimal."""

    standard_types = (
        "list",
        "unicode",
        "str",
        "int",
        "long",
        "float",
        "bool",
        "NoneType",
    )

    def default(self, obj):
        """Convert non-standard types to a JSON-compatible format."""
        if obj.__class__.__name__ not in self.standard_types:
            if isinstance(obj, datetime.datetime):
                return {"object": repr(obj).replace(", tzinfo=<UTC>", "")}
            elif hasattr(obj, "tolist"):  # Handle numpy arrays or similar
                return obj.tolist()
            else:
                return {"object": repr(obj)}
        return super().default(obj)


def as_complex(dct):
    """Convert JSON objects back to their original Python types."""
    if "object" in dct:
        try:
            return eval(dct["object"])
        except (NameError, SyntaxError):
            return None
    return dct


def dumps(obj):
    """Encode a Python object to a JSON string and URL-encode it.

    Args:
        obj: Python object to encode.

    Returns:
        str: URL-encoded JSON string.
    """
    try:
        return quote_plus(json.dumps(obj, cls=ComplexEncoder))
    except (TypeError, ValueError) as e:
        raise ValueError(f"Failed to encode object: {e}")


def loads(json_str):
    """Decode a URL-encoded JSON string to a Python object.

    Args:
        json_str: URL-encoded JSON string.

    Returns:
        object: Decoded Python object.
    """
    try:
        return json.loads(unquote_plus(json_str), object_hook=as_complex)
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to decode JSON string: {e}")


def json_dumps(obj, indent=None):
    """Encode a Python object to a JSON string.

    Args:
        obj: Python object to encode.
        indent: Optional indentation for pretty-printing.

    Returns:
        str: JSON-encoded string.
    """
    try:
        return json.dumps(obj, cls=ComplexEncoder, indent=indent)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Failed to encode object: {e}")


def json_loads(json_str):
    """Decode a JSON string to a Python object.

    Args:
        json_str: JSON-encoded string.

    Returns:
        object: Decoded Python object.
    """
    try:
        return json.loads(json_str, object_hook=as_complex)
    except (ValueError, json.JSONDecodeError) as e:
        raise ValueError(f"Failed to decode JSON string: {e}")


class ComplexDecoder(json.JSONDecoder):
    """Custom JSON decoder that uses the as_complex function for object conversion."""

    def decode(self, s):
        """Decode a JSON string to a Python object.

        Args:
            s: JSON-encoded string.

        Returns:
            object: Decoded Python object.
        """
        return json_loads(s)
