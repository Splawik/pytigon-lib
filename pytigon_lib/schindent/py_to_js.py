"""
Python-to-JavaScript compilation using PScript.

Provides utilities for:
- Compiling Python code to JavaScript
- Custom class definition generation for JS output
- Python code preparation with export detection
- Monkey-patching PScript parser for enhanced class support
"""

import logging
import sys
import traceback
from typing import List, Tuple

import pscript
import pscript.parser2
from pscript import stdlib
from pscript.parser1 import JSError, reprs

logger = logging.getLogger(__name__)


def get_class_definition(
    name: str, base: str = "Object", docstring: str = ""
) -> List[str]:
    """Generate JavaScript class definition lines from Python class info.

    Produces JS code that creates a class constructor with proper prototype
    chain setup. Supports window-based base classes with Reflect.construct.

    Args:
        name: The class name for the JavaScript output.
        base: The base class name (default "Object").
        docstring: Optional docstring to include as comments.

    Returns:
        List of JavaScript source lines defining the class.
    """
    code = []

    code.append(f"{name} = function () {{")

    for line in docstring.splitlines():
        code.append(f"    // {line}")

    if base.startswith("window."):
        code.append("    var obj;")
        code.append("    if ('js_get_base_arguments' in this) {")
        code.append(
            f"        obj = Reflect.construct("
            f"{base.split('.')[1]}, "
            f"this.js_get_base_arguments(arguments), "
            f"{name});"
        )
        code.append("    } else {")
        code.append(
            f"        obj = Reflect.construct({base.split('.')[1]}, [], {name});"
        )
        code.append("    }")
        code.append(f"    {stdlib.FUNCTION_PREFIX}op_instantiate(obj, arguments);")
        code.append("    return obj")
    else:
        code.append(f"    {stdlib.FUNCTION_PREFIX}op_instantiate(this, arguments);")

    code.append("}")

    if base != "Object":
        code.append(f"{name}.prototype = Object.create({base});")
    code.append(f"{name}.prototype._base_class = {base};")
    code.append(f"{name}.prototype.__name__ = {reprs(name.split('.')[-1])};")

    code.append("")
    return code


# Monkey-patch PScript's class definition generator
pscript.parser2.get_class_definition = get_class_definition


def parse_ClassDef(self, node) -> List[str]:
    """Custom class definition parser for PScript.

    Handles Python class definitions with enhanced support for
    window-based base classes and proper docstring handling.

    Args:
        self: Parser2 instance.
        node: AST node representing a ClassDef.

    Returns:
        List of JavaScript source lines for the class definition.

    Raises:
        JSError: On unsupported features (multiple inheritance,
                 metaclasses, class decorators, complex base names).
    """
    # Validate class definition
    if len(node.arg_nodes) > 1:
        raise JSError("Multiple inheritance not (yet) supported.")
    if node.kwarg_nodes:
        raise JSError("Metaclasses not supported.")
    if node.decorator_nodes:
        raise JSError("Class decorators not supported.")

    # Determine base class
    base_class = "Object"
    if node.arg_nodes:
        base_class = "".join(self.parse(node.arg_nodes[0]))

    if not base_class.replace("window.", "").replace(".", "_").isalnum():
        raise JSError("Base classes must be simple names")
    elif base_class.lower() == "object":
        base_class = "Object"
    else:
        base_class = base_class + ".prototype"

    # Build class constructor
    code = []
    docstring = self.pop_docstring(node)
    docstring = docstring if self._docstrings else ""

    for line in get_class_definition(node.name, base_class, docstring):
        code.append(self.lf(line))

    self.use_std_function("op_instantiate", [])

    # Process class body
    self.vars.add(node.name)
    self._seen_class_names.add(node.name)
    self.push_stack("class", node.name)

    for sub in node.body_nodes:
        code += self.parse(sub)

    code.append("\n")
    self.pop_stack()

    return code


# Monkey-patch PScript's ClassDef parser
pscript.parser2.Parser2.parse_ClassDef = parse_ClassDef


def prepare_python_code(code: str) -> str:
    """Prepare Python code for JS compilation by adding export statements.

    Scans Python code for top-level function and class definitions
    (excluding private ones starting with '_') and adds a RawJS export
    statement for them.

    Args:
        code: Python source code to prepare.

    Returns:
        Modified Python code with export statement appended if public
        functions/classes are found.
    """
    exported_ids: List[str] = []

    for line in code.split("\n"):
        stripped = line.strip()
        if (stripped.startswith("def ") and not stripped.startswith("def _")) or (
            stripped.startswith("class ") and not stripped.startswith("class _")
        ):
            try:
                # Extract identifier: "def func_name(...)" -> "func_name"
                identifier = stripped.split()[1].split("(")[0].split(":")[0]
                exported_ids.append(identifier)
            except IndexError:
                continue

    if exported_ids:
        code += f"\n\nRawJS('export {{{', '.join(exported_ids)}}}')\n"

    return code


def compile(python_code: str) -> Tuple[bool, str]:
    """Compile Python code to JavaScript using PScript.

    Args:
        python_code: Python source code to compile.

    Returns:
        A tuple of (has_error, result) where:
        - has_error is True if compilation failed, False on success
        - result is the JavaScript code on success, or error message on failure
    """
    try:
        prepared = prepare_python_code(python_code)
        js = pscript.py2js(prepared, inline_stdlib=False)
        return (False, js)
    except Exception:
        error_message = "".join(traceback.format_exception(*sys.exc_info()))
        logger.error("Python-to-JS compilation failed:\n%s", error_message)
        return (True, error_message)
