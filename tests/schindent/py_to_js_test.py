from pytigon_lib.schindent.py_to_js import *

# Pytest tests
import pytest


def test_compile_success():
    code = "def foo(): pass"
    error, js = compile(code)
    assert not error
    assert "foo = function" in js


def test_compile_failure():
    code = "def foo("  # Invalid syntax
    error, js = compile(code)
    assert "SyntaxError" in js
    assert error


if __name__ == "__main__":
    pytest.main()
