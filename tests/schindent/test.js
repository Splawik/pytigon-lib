Traceback (most recent call last):
  File "/home/sch/.local/lib/python3.13/site-packages/pytigon_lib/schindent/py_to_js.py", line 47, in compile
    js = pscript.py2js(prepare_python_code(python_code), inline_stdlib=False)
  File "/home/sch/.local/lib/python3.13/site-packages/pscript/functions.py", line 148, in py2js
    return py2js_(ob)
  File "/home/sch/.local/lib/python3.13/site-packages/pscript/functions.py", line 115, in py2js_
    p = Parser(pycode, **parser_options)
  File "/home/sch/.local/lib/python3.13/site-packages/pscript/parser0.py", line 252, in __init__
    raise (err)
  File "/home/sch/.local/lib/python3.13/site-packages/pscript/parser0.py", line 242, in __init__
    self._parts = self.parse(self._root)
                  ~~~~~~~~~~^^^^^^^^^^^^
  File "/home/sch/.local/lib/python3.13/site-packages/pscript/parser0.py", line 421, in parse
    res = parse_func(node)
  File "/home/sch/.local/lib/python3.13/site-packages/pscript/parser1.py", line 947, in parse_Module
    code += self.parse(child)
            ~~~~~~~~~~^^^^^^^
  File "/home/sch/.local/lib/python3.13/site-packages/pscript/parser0.py", line 421, in parse
    res = parse_func(node)
  File "/home/sch/.local/lib/python3.13/site-packages/pscript/parser1.py", line 928, in parse_Import
    raise JSError("PScript does not support imports.")
pscript.parser0.JSError: Error processing Import-node, line 1, col 0:
PScript does not support imports.
