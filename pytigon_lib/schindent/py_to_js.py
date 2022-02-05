import sys
import pscript
import traceback


def prepare_python_code(code):
    exported_id = []
    for line in code.split("\n"):
        if (line.startswith("def") and not line.startswith("def _")) or (
            line.startswith("class") and not line.startswith("class _")
        ):
            try:
                exported_id.append(line.split(" ")[1].split("(")[0].split(":")[0])
            except:
                pass

    if exported_id:
        code += "\n\nRawJS('export {" + ", ".join(exported_id) + "}')\n"

    return code


def compile(python_code):
    error = False
    try:
        js = pscript.py2js(prepare_python_code(python_code), inline_stdlib=False)
        return (error, js)
    except Exception as e:
        error = True
        exc_info = sys.exc_info()
        js = "".join(traceback.format_exception(*exc_info))
        del exc_info
    return (error, js)
