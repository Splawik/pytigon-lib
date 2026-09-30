"""Common utility functions: string handling, introspection, encoding, dict operations."""

import os
import platform
import sys
import types
from base64 import b64decode, b64encode
from collections.abc import Mapping as MappingABC


def split2(txt, sep):
    """Split a string into two parts at the first occurrence of *sep*.

    Equivalent to ``txt.partition(sep)`` without the separator. Kept as a
    named helper because callers outside this package still use it.

    Args:
        txt: The string to split.
        sep: The separator to search for.

    Returns:
        A tuple ``(before_sep, after_sep)``. If *sep* is not found,
        the second element is an empty string.
    """
    before, _sep, after = txt.partition(sep)
    return before, after


def extend_fun_to(obj):
    """Decorator that binds a function as a method on *obj*.

    Usage::

        @extend_fun_to(my_object)
        def my_method(self, arg):
            ...

    Args:
        obj: The target object to attach the method to.

    Returns:
        A decorator that installs the function as a bound method.
    """

    def decorator(func):
        setattr(obj, func.__name__, types.MethodType(func, obj))
        return func

    return decorator


def bencode(s):
    """Base64-encode a string and return the result as a UTF-8 string.

    Args:
        s: The string to encode (str or bytes).

    Returns:
        Base64-encoded string.
    """
    if isinstance(s, str):
        s = s.encode("utf-8")
    return b64encode(s).decode("ascii")


def bdecode(s):
    """Base64-decode a string and return the result as a UTF-8 string.

    Args:
        s: The base64-encoded string (str or bytes).

    Returns:
        Decoded string.
    """
    if isinstance(s, str):
        s = s.encode("ascii")
    return b64decode(s).decode("utf-8")


def clean_href(href):
    """Strip newlines and whitespace from an href/URL string.

    Args:
        href: The URL string to clean.

    Returns:
        Cleaned URL string.
    """
    return href.replace("\n", "").strip()


def is_null(value, value2):
    """Return *value* if it is truthy, otherwise return *value2*.

    This is a null-coalescing helper for template contexts.

    Args:
        value: Primary value.
        value2: Fallback value.

    Returns:
        *value* if truthy, else *value2*.
    """
    return value if value else value2


def get_executable():
    """Return the path to the current Python interpreter executable.

    Handles cases where ``sys.executable`` points to a non-Python wrapper
    (e.g. when embedded) by falling back to ``sys.prefix``.

    Returns:
        Absolute path to the Python executable.
    """
    executable = sys.executable
    executable_name = os.path.basename(executable.replace("\\", "/"))
    if "python" in executable_name or "pypy" in executable_name:
        return executable
    # Fallback: construct path from the standard library location
    if platform.system() == "Windows":
        return os.path.join(os.path.dirname(os.__file__), "python.exe")
    # Unix: replace lib/pythonX.Y with bin/python
    lib_python_dir = os.path.dirname(os.__file__)
    base_dir = os.path.dirname(os.path.dirname(lib_python_dir))
    return os.path.join(base_dir, "bin", "python")


def norm_indent(text):
    """Normalize indentation by stripping common leading whitespace.

    The indentation level is determined by the first non-empty line.

    Args:
        text: A multi-line string or list of strings.

    Returns:
        Normalized string with common indentation removed.
    """
    if isinstance(text, str):
        lines = text.replace("\r", "").split("\n")
    else:
        lines = list(text)
    indent = -1
    result = []
    for line in lines:
        if indent < 0:
            stripped = line.lstrip()
            if stripped:
                indent = len(line) - len(stripped)
        if indent >= 0:
            result.append(line[indent:])
        else:
            result.append(line)
    return "\n".join(result)


def get_request():
    """Walk the call stack to find the current Django request object.

    Looks for a local variable named ``request`` whose value exposes a
    ``session`` attribute. The frame chain is walked directly with
    ``sys._getframe()``; ``inspect.stack()`` would build a ``FrameInfo`` (with
    source context and linecache lookups) for every frame on the stack, which
    is far too expensive for a template-rendering hot path.

    Returns:
        The request object, or None if not found.
    """
    try:
        frame = sys._getframe(1)
    except ValueError:  # pragma: no cover - no frame beyond the top
        return None
    try:
        while frame is not None:
            request = frame.f_locals.get("request")
            if request is not None and hasattr(request, "session"):
                return request
            frame = frame.f_back
    finally:
        del frame
    return None


def get_session():
    """Retrieve the current Django session from the request.

    Returns:
        The session object, or None if no request is active.
    """
    request = get_request()
    return request.session if request else None


def is_in_dicts(elem, dicts):
    """Check if *elem* is a key in any dictionary from *dicts*.

    Args:
        elem: The key to search for.
        dicts: An iterable of dictionaries.

    Returns:
        True if *elem* is found in any dictionary.
    """
    return any(elem in d for d in dicts)


def get_from_dicts(elem, dicts):
    """Get the value for *elem* from the first dictionary that has it.

    Args:
        elem: The key to look up.
        dicts: An iterable of dictionaries.

    Returns:
        The value from the first matching dictionary, or None.
    """
    for d in dicts:
        if elem in d:
            return d[elem]
    return None


def update_nested_dict(d, u):
    """Recursively update dictionary *d* with values from *u*.

    Nested dictionaries are merged rather than replaced.

    Args:
        d: The dictionary to update (modified in place).
        u: The dictionary with new values.

    Returns:
        The updated dictionary *d*.
    """
    for k, v in u.items():
        if isinstance(v, MappingABC):
            d[k] = update_nested_dict(d.get(k, {}), v)
        else:
            d[k] = v
    return d


def transform_backslash_input_str(s):
    return s.replace("\\\\", "[$Backward SlashBackward Slash$]").replace(
        "\\n", "[$Backward Slash n$]"
    )


def transform_backslash_output_str(s):
    return s.replace("[$Backward SlashBackward Slash$]", "\\").replace(
        "[$Backward Slash n$]", "\n"
    )
