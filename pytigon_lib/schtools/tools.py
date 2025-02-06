import types
import sys
import os
import platform
import inspect
from collections import abc
from base64 import b64encode, b64decode


def split2(txt, sep):
    """Split `txt` into two parts based on the first occurrence of `sep`.
    If `sep` is not found, the second part is an empty string.
    """
    idx = txt.find(sep)
    if idx >= 0:
        return txt[:idx], txt[idx + len(sep) :]
    return txt, ""


def extend_fun_to(obj):
    """Decorator to extend `obj` with the decorated function."""

    def decorator(func):
        setattr(obj, func.__name__, types.MethodType(func, obj))
        return func

    return decorator


def bencode(s):
    """Encode string `s` using base64 encoding."""
    if isinstance(s, str):
        s = s.encode("utf-8")
    return b64encode(s).decode("utf-8")


def bdecode(s):
    """Decode a base64 encoded string."""
    if isinstance(s, str):
        s = s.encode("utf-8")
    return b64decode(s).decode("utf-8")


def clean_href(href):
    """Remove newlines and strip whitespace from `href`."""
    return href.replace("\n", "").strip()


def is_null(value, value2):
    """Return `value` if it is truthy, otherwise return `value2`."""
    return value if value else value2


def get_executable():
    """Get the path to the current Python executable."""
    executable = sys.executable
    executable_name = executable.replace("\\", "/").split("/")[-1]
    if "python" in executable_name or "pypy" in executable_name:
        return executable
    if platform.system() == "Windows":
        return os.path.join(os.path.dirname(os.__file__), "python.exe")
    return os.path.join(
        os.path.dirname(os.__file__).replace("/lib/python", "/bin/python")
    )


def norm_indent(text):
    """Normalize indentation of a multi-line string."""
    if isinstance(text, str):
        lines = text.replace("\r", "").split("\n")
    else:
        lines = text
    indent = -1
    result = []
    for line in lines:
        if indent < 0:
            indent = len(line) - len(line.lstrip())
        result.append(line[indent:])
    return "\n".join(result) if indent >= 0 else ""


def get_request():
    """Retrieve the request object from the call stack."""
    frame = None
    try:
        for frame_info in inspect.stack()[1:]:
            frame = frame_info.frame
            code = frame.f_code
            if code.co_varnames[:1] == ("request",) and "request" in frame.f_locals:
                request = frame.f_locals["request"]
            elif (
                code.co_varnames[:2] == ("self", "request")
                and "request" in frame.f_locals
            ):
                request = frame.f_locals["request"]
            else:
                continue
            if hasattr(request, "session"):
                return request
    finally:
        if frame:
            del frame
    return None


def get_session():
    """Retrieve the session from the request object."""
    request = get_request()
    return request.session if request else None


def is_in_dicts(elem, dicts):
    """Check if `elem` exists in any of the dictionaries in `dicts`."""
    return any(elem in d for d in dicts)


def get_from_dicts(elem, dicts):
    """Retrieve the value of `elem` from the first dictionary in `dicts` that contains it."""
    for d in dicts:
        if elem in d:
            return d[elem]
    return None


def is_in_cancan_rules(model, rules):
    """Check if `model` is a subject in any of the `rules`."""
    return any(rule["subject"] == model for rule in rules)


def update_nested_dict(d, u):
    """Recursively update dictionary `d` with values from dictionary `u`."""
    for k, v in u.items():
        if isinstance(v, abc.Mapping):
            d[k] = update_nested_dict(d.get(k, {}), v)
        else:
            d[k] = v
    return d
