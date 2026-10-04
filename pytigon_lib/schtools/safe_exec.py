"""Execution helpers for code that comes from configuration, not from Python.

Pytigon evaluates code that lives *outside* the source tree: ``<calc>`` bodies
in HTML, ``*_build.py`` scripts in a project, definitions stored in the
database, and scheduler specs. This module is the single place that decides how
much to trust such code. (Decoded JSON no longer reaches this module:
``schjson`` reconstructs values structurally and never evaluates them.)

Why this is not a sandbox
-------------------------
An earlier version restricted ``__builtins__`` and documented that "attribute
access, imports, and I/O are blocked". That was false, and worse than useless:
``().__class__.__base__.__subclasses__()`` walked straight out of it to
``BuiltinImporter`` and from there to ``os.system``, in a single expression. A
restriction that is trivially bypassable gives a false sense of safety, so this
module does not pretend to be one.

What is actually enforced
-------------------------
CPython cannot be contained from inside Python. What *can* be stopped is the
specific idiom that turns "a value someone typed" into "arbitrary code
execution": the introspection ladder

    object -> __class__ -> __base__/__bases__ -> __subclasses__ -> the class
    that can load modules -> any module -> os.system

:data:`_FORBIDDEN_ATTRS` and :data:`_FORBIDDEN_NAMES` name every rung of that
ladder, plus the dynamic-attribute variants (``getattr(obj, "__class__")``,
which is checked for string-literal names), plus re-entering the interpreter via
``eval``/``exec``/``compile``/``__import__``.

Everything else is allowed on purpose. Imports work, file access works, and
whole programs run, because that is how Pytigon is actually used: it is a local
application that executes its own project's build scripts, and scripts an
administrator stored in the database. Locking that down would break the product
without protecting anything an attacker could not already do by editing a file
on disk.

Residual risk, stated plainly: this raises the cost of an accidental or naive
escalation from a data field to code execution. It is not a boundary against a
determined attacker, who can still write a payload that never touches a
forbidden name. For untrusted input, run the code in a separate process.
"""

import ast
import builtins
from typing import Any, NamedTuple

__all__ = [
    "EvalResult",
    "ForbiddenConstruct",
    "safe_eval",
    "safe_exec",
    "validate_source",
]


class EvalResult(NamedTuple):
    value: Any
    error: Exception | None


class ForbiddenConstruct(ValueError):
    """Raised when source uses an interpreter-introspection construct."""


# Rungs of the escape ladder. Every one of these is reachable from ordinary
# values, which is exactly what makes them dangerous.
_FORBIDDEN_ATTRS = frozenset(
    {
        # reach the type system and walk it to `object`
        "__class__",
        "__base__",
        "__bases__",
        "__mro__",
        "__subclasses__",
        "__subclasshook__",
        "__init_subclass__",
        # reach a frame or a code object and read its globals
        "__globals__",
        "__code__",
        "__closure__",
        "__func__",
        "__self__",
        "__defaults__",
        "__kwdefaults__",
        "__init__",
        # reach the import machinery
        "__builtins__",
        "__loader__",
        "__spec__",
        # reach raw namespaces
        "__dict__",
        # pickle-style object surgery
        "__reduce__",
        "__reduce_ex__",
        # attribute machinery
        "__getattribute__",
        "__setattr__",
        "__delattr__",
    }
)

# Bare names that re-enter the interpreter and so bypass the AST walk above.
_FORBIDDEN_NAMES = frozenset(
    {
        "__import__",
        "__builtins__",
        "eval",
        "exec",
        "compile",
    }
)

# Dynamic accessors and the position of their *name* argument. The name is
# never the first argument - that is the object being inspected - so the
# wrong index would silently check nothing.
_NAME_ARG_POSITION = {
    "getattr": 1,
    "setattr": 1,
    "delattr": 1,
    "hasattr": 1,
}


def _const_str(node: ast.AST) -> str | None:
    """Return a string literal if *node* is a constant expression.

    Folds plain constants, ``"a" + "b"`` concatenations and the literal parts
    of an f-string, so ``getattr(x, "__cl" + "ass__")`` is still recognised.
    Returns None when the value is not statically known.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        left = _const_str(node.left)
        right = _const_str(node.right)
        if left is not None and right is not None:
            return left + right
    if isinstance(node, ast.JoinedStr):
        parts = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                return None
        return "".join(parts)
    return None


class _Validator(ast.NodeVisitor):
    """Reject the escape ladder, leave everything else alone."""

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in _FORBIDDEN_ATTRS:
            raise ForbiddenConstruct(
                f"attribute {node.attr!r} is not allowed in evaluated code "
                f"(line {node.lineno}): it exposes the interpreter internals"
            )
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Load) and node.id in _FORBIDDEN_NAMES:
            raise ForbiddenConstruct(
                f"name {node.id!r} is not allowed in evaluated code "
                f"(line {node.lineno}): it re-enters the interpreter"
            )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        target = node.func
        name = target.id if isinstance(target, ast.Name) else None
        position = _NAME_ARG_POSITION.get(name)
        if position is not None:
            # Covers both getattr(x, "__class__") and getattr(x, name="...").
            arg = None
            if len(node.args) > position:
                arg = node.args[position]
            else:
                for keyword in node.keywords:
                    if keyword.arg == "name":
                        arg = keyword.value
                        break
            if arg is not None:
                literal = _const_str(arg)
                if literal is not None and literal in _FORBIDDEN_ATTRS:
                    raise ForbiddenConstruct(
                        f"{name}(..., {literal!r}) is not allowed in evaluated "
                        f"code (line {node.lineno}): it reaches the "
                        f"interpreter internals"
                    )
        self.generic_visit(node)


def validate_source(source: str, mode: str = "exec") -> ast.AST:
    """Parse *source* and reject interpreter-introspection constructs.

    Args:
        source: Python source text.
        mode: ``"eval"`` for a single expression, ``"exec"`` for statements.

    Returns:
        The parsed :class:`ast.AST`.

    Raises:
        SyntaxError: If *source* does not parse in the requested *mode*.
        ForbiddenConstruct: If it uses a construct that would expose the
            interpreter's object model or re-enter the interpreter.
    """
    tree = ast.parse(source, mode=mode)
    _Validator().visit(tree)
    return tree


def _globals(extra_globals: dict[str, Any] | None, name: str) -> dict[str, Any]:
    """Build the globals mapping handed to eval/exec.

    Builtins are deliberately the *full* set: Pytigon runs its own project's
    scripts, so hiding builtins would break imports and I/O without closing any
    hole. :func:`validate_source` is what enforces the policy.
    """
    glob: dict[str, Any] = {"__name__": name, "__builtins__": builtins}
    if extra_globals:
        glob.update(extra_globals)
    return glob


def safe_eval(
    expression: str,
    extra_globals: dict[str, Any] | None = None,
    local_ns: dict[str, Any] | None = None,
) -> Any:
    """Evaluate a Python *expression* after validating it.

    Statements are rejected (``mode="eval"``), as are the introspection
    constructs listed in :data:`_FORBIDDEN_ATTRS`. Attribute access, calls and
    the full set of builtins are otherwise available, so decoded values such as
    ``datetime.datetime(2024, 1, 1)`` and ``Decimal("1.5")`` round-trip.

    Args:
        expression: A Python expression string.
        extra_globals: Optional additional names to expose.
        local_ns: Optional local namespace; a fresh dict if not provided.

    Returns:
        The value of the expression.

    Raises:
        SyntaxError: If *expression* is not a single valid expression.
        ForbiddenConstruct: If it uses a forbidden construct.
    """
    validate_source(expression, mode="eval")
    if local_ns is None:
        local_ns = {}
    return eval(expression, _globals(extra_globals, "safe_eval"), local_ns)


def safe_exec(
    source: str,
    extra_globals: dict[str, Any] | None = None,
    local_ns: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute Python *source* after validating it.

    Imports, file access and the full set of builtins are available: the
    callers are the project's own ``*_build.py`` scripts, database-stored
    definitions and ``fastform`` sources, which all need them. Only the
    introspection constructs in :data:`_FORBIDDEN_ATTRS` are rejected.

    Args:
        source: Python source code (statements, not just an expression).
        extra_globals: Optional additional names to expose.
        local_ns: Optional local namespace; a fresh dict if not provided.

    Returns:
        The local namespace dict after execution, so callers can pick up the
        functions and classes the code defined.

    Raises:
        SyntaxError: If *source* does not parse.
        ForbiddenConstruct: If it uses a forbidden construct.
    """
    validate_source(source, mode="exec")
    if local_ns is None:
        local_ns = {}
    exec(source, _globals(extra_globals, "safe_exec"), local_ns)
    return local_ns
