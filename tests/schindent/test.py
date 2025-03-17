from pytigon_lib.schindent.indent_style import ihtml_to_html_base
from pytigon_lib.schindent.html2ihtml import convert
from pytigon_lib.schindent.py_to_js import compile
from pytigon_lib.schindent.indent_tools import convert_js

import pytigon_lib.schdjangoext.django_mini_init  # noqa: F401

convert("./test.html", "./test.ihtml")

with open("./test2.html", "wt") as f:
    f.write(ihtml_to_html_base("./test.ihtml"))

with open("./test2.py", "rt") as f_in, open("./test2.js", "wt") as f_out:
    error, js = compile(f_in.read())
    f_out.write(js)

with open("./test3.ijs", "rt") as f_in, open("./test3.js", "wt") as f_out:
    convert_js(f_in, f_out)


from django.core.files.storage import default_storage
import os
import sys

BASE_PATH = os.path.abspath(os.getcwd())
default_storage.fs.mount("cwd", BASE_PATH)
ihtml_file_path = os.path.join("/cwd", sys.argv[-1])
f = default_storage.open(ihtml_file_path)
