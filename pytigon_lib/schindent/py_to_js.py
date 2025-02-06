import sys
import pscript
import traceback
from typing import Tuple, List


def prepare_python_code(code: str) -> str:
    """
    Prepares Python code for compilation by identifying exported functions and classes.

    Args:
        code (str): The Python code to be prepared.

    Returns:
        str: The modified Python code with export statements for identified functions and classes.
    """
    exported_id: List[str] = []

    for line in code.split("\n"):
        if (line.startswith("def") and not line.startswith("def _")) or (
            line.startswith("class") and not line.startswith("class _")
        ):
            try:
                identifier = line.split(" ")[1].split("(")[0].split(":")[0]
                exported_id.append(identifier)
            except IndexError:
                continue

    if exported_id:
        code += f"\n\nRawJS('export {{{", ".join(exported_id)}}}')\n"

    return code


def compile(python_code: str) -> Tuple[bool, str]:
    """
    Compiles Python code to JavaScript using PScript.

    Args:
        python_code (str): The Python code to be compiled.

    Returns:
        Tuple[bool, str]: A tuple containing a boolean indicating success or failure,
                          and the resulting JavaScript code or error message.
    """
    try:
        js = pscript.py2js(prepare_python_code(python_code), inline_stdlib=False)
        return (False, js)
    except Exception as e:
        error_message = "".join(traceback.format_exception(*sys.exc_info()))
        return (True, error_message)
