"""Extra tests for :mod:`pytigon_lib.schindent.py_to_js`."""
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schindent.py_to_js import (
    compile,
    get_class_definition,
    prepare_python_code,
)


class TestGetClassDefinition:
    def test_simple_class_no_base(self):
        result = get_class_definition("MyClass")
        assert "MyClass = function" in result[0]
        assert isinstance(result, list)

    def test_class_with_object_base(self):
        result = get_class_definition("MyClass", "Object")
        assert "op_instantiate(this, arguments)" in "\n".join(result)

    def test_class_with_window_base(self):
        result = get_class_definition("MyClass", "window.HTMLElement")
        assert "Reflect.construct" in "\n".join(result)

    def test_class_with_docstring(self):
        result = get_class_definition("MyClass", "Object", "My docstring\nSecond line")
        assert "My docstring" in "\n".join(result)
        assert "Second line" in "\n".join(result)

    def test_class_has_prototype_chain(self):
        result = get_class_definition("TestClass", "ParentClass")
        joined = "\n".join(result)
        assert "TestClass.prototype = Object.create(ParentClass)" in joined
        assert "TestClass.prototype._base_class = ParentClass" in joined

    def test_class_has_name_attribute(self):
        result = get_class_definition("MyApp.MyClass", "Object")
        joined = "\n".join(result)
        assert "__name__" in joined

    def test_class_no_base_skips_prototype_create(self):
        result = get_class_definition("SimpleClass", "Object")
        joined = "\n".join(result)
        assert "Object.create(Object)" not in joined

    def test_class_ends_with_empty_line(self):
        result = get_class_definition("Test")
        assert result[-1] == ""

    def test_class_is_list_of_strings(self):
        result = get_class_definition("Test", "Object")
        assert all(isinstance(line, str) for line in result)


class TestPreparePythonCode:
    def test_simple_function(self):
        code = "def foo():\n    pass\n"
        result = prepare_python_code(code, True)
        assert "export" in result

    def test_simple_class(self):
        code = "class Bar:\n    pass\n"
        result = prepare_python_code(code, True)
        assert "export" in result

    def test_private_function_skipped(self):
        code = "def _private():\n    pass\n"
        result = prepare_python_code(code, True)
        assert "export" not in result

    def test_private_class_skipped(self):
        code = "class _Private:\n    pass\n"
        result = prepare_python_code(code, True)
        assert "export" not in result

    def test_no_public_exports(self):
        code = "def _private():\n    pass\nclass _Internal:\n    pass\n"
        result = prepare_python_code(code, True)
        assert "export" not in result

    def test_append_exports_false(self):
        code = "def foo():\n    pass\n"
        result = prepare_python_code(code, False)
        assert "export" not in result

    def test_multiple_exports(self):
        code = "def foo():\n    pass\ndef bar():\n    pass\nclass Baz:\n    pass\n"
        result = prepare_python_code(code, True)
        assert "foo" in result
        assert "bar" in result
        assert "Baz" in result

    def test_no_append_exports_no_exports(self):
        code = "def _private():\n    pass\n"
        result = prepare_python_code(code, True)
        assert result == code


class TestCompileExtra:
    def test_compile_success_tuple(self):
        code = "def foo():\n    pass\n"
        error, js = compile(code)
        assert isinstance(error, bool)
        assert isinstance(js, str)

    def test_compile_failure_tuple(self):
        code = "def foo("
        error, js = compile(code)
        assert error is True
        assert "SyntaxError" in js

    def test_compile_class(self):
        code = "class Foo:\n    pass\n"
        error, js = compile(code)
        assert not error
        assert "Foo" in js

    def test_compile_simple_function(self):
        code = "def foo():\n    x = 1\n    return x\n"
        error, js = compile(code)
        assert not error
