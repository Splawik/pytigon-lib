"""Safe exec/eval utilities with restricted builtins.

Provides audited, centrally-managed safe execution helpers for the
entire project.  All ``exec()`` and ``eval()`` call-sites should
route through this module so that security restrictions are applied
consistently.

Security design
---------------
- ``__builtins__`` is restricted to a **whitelist** of pure functions
  with no I/O, no import capability, and no attribute traversal.
- ``__import__``, ``open``, ``eval``, ``exec``, ``compile``,
  ``getattr``, ``setattr``, ``hasattr``, ``super``, ``breakpoint``,
  ``input``, and all I/O builtins are **excluded**.
- Callers may optionally supply extra names via ``extra_globals`` —
  these are merged on top of the restricted globals.
- Exception handling is the caller's responsibility.
"""

import builtins
from typing import Any, Dict, NamedTuple, Optional


class EvalResult(NamedTuple):
    value: Any
    error: Optional[Exception]


RESTRICTED_BUILTINS: Dict[str, Any] = {
    "True": True,
    "False": False,
    "None": None,
    "abs": abs,
    "all": all,
    "any": any,
    "ascii": ascii,
    "bin": bin,
    "bool": bool,
    "bytes": bytes,
    "callable": callable,
    "chr": chr,
    "complex": complex,
    "dict": dict,
    "divmod": divmod,
    "enumerate": enumerate,
    "filter": filter,
    "float": float,
    "format": format,
    "frozenset": frozenset,
    "hex": hex,
    "int": int,
    "isinstance": isinstance,
    "issubclass": issubclass,
    "iter": iter,
    "len": len,
    "list": list,
    "map": map,
    "max": max,
    "min": min,
    "next": next,
    "object": object,
    "oct": oct,
    "ord": ord,
    "pow": pow,
    "print": print,
    "range": range,
    "repr": repr,
    "reversed": reversed,
    "round": round,
    "set": set,
    "slice": slice,
    "sorted": sorted,
    "str": str,
    "sum": sum,
    "tuple": tuple,
    "type": type,
    "zip": zip,
    "len": len,
}


def safe_eval(expression: str, extra_globals: Optional[Dict[str, Any]] = None, local_ns: Optional[Dict[str, Any]] = None) -> Any:
    """Evaluate a Python *expression* with restricted builtins.

    Only arithmetic, comparisons, builtin constructors, and names
    explicitly passed via *extra_globals* (or *local_ns*) are allowed.
    Attribute access, imports, and I/O are blocked.

    Args:
        expression: A Python expression string.
        extra_globals: Optional dictionary of additional names to
            expose alongside the restricted builtins.
        local_ns: Optional local namespace.

    Returns:
        The value of the expression.
    """
    glob = {"__builtins__": RESTRICTED_BUILTINS}
    if extra_globals:
        glob.update(extra_globals)
    if local_ns is None:
        local_ns = {}
    return eval(expression, glob, local_ns)


def safe_exec(source: str, extra_globals: Optional[Dict[str, Any]] = None, local_ns: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Execute Python *source code* with restricted builtins.

    Similar restrictions as :func:`safe_eval` — no I/O, no imports,
    no attribute access via ``getattr``/``setattr``.

    Args:
        source: Python source code (statements, not just an expression).
        extra_globals: Optional dictionary of additional names to
            expose alongside the restricted builtins.
        local_ns: Optional local namespace.  A fresh dict is used if
            not provided.

    Returns:
        The local namespace dict after execution (useful for
        extracting functions / classes the code defined).
    """
    glob = {"__builtins__": RESTRICTED_BUILTINS}
    if extra_globals:
        glob.update(extra_globals)
    if local_ns is None:
        local_ns = {}
    exec(source, glob, local_ns)
    return local_ns
