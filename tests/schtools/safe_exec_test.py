"""Tests for :mod:`pytigon_lib.schtools.safe_exec`."""
import pytest

from pytigon_lib.schtools.safe_exec import (
    EvalResult,
    RESTRICTED_BUILTINS,
    safe_eval,
    safe_exec,
)


class TestRestrictedBuiltins:
    """Tests for the restricted builtins whitelist."""

    def test_allows_arithmetic(self):
        assert "abs" in RESTRICTED_BUILTINS
        assert "max" in RESTRICTED_BUILTINS
        assert "min" in RESTRICTED_BUILTINS
        assert "sum" in RESTRICTED_BUILTINS
        assert "pow" in RESTRICTED_BUILTINS
        assert "round" in RESTRICTED_BUILTINS

    def test_allows_basic_types(self):
        assert "int" in RESTRICTED_BUILTINS
        assert "str" in RESTRICTED_BUILTINS
        assert "float" in RESTRICTED_BUILTINS
        assert "bool" in RESTRICTED_BUILTINS
        assert "bytes" in RESTRICTED_BUILTINS
        assert "list" in RESTRICTED_BUILTINS
        assert "dict" in RESTRICTED_BUILTINS
        assert "tuple" in RESTRICTED_BUILTINS
        assert "set" in RESTRICTED_BUILTINS

    def test_allows_iterators(self):
        assert "range" in RESTRICTED_BUILTINS
        assert "enumerate" in RESTRICTED_BUILTINS
        assert "zip" in RESTRICTED_BUILTINS
        assert "map" in RESTRICTED_BUILTINS
        assert "filter" in RESTRICTED_BUILTINS
        assert "sorted" in RESTRICTED_BUILTINS
        assert "reversed" in RESTRICTED_BUILTINS

    def test_allows_string_operations(self):
        assert "ord" in RESTRICTED_BUILTINS
        assert "chr" in RESTRICTED_BUILTINS
        assert "repr" in RESTRICTED_BUILTINS
        assert "ascii" in RESTRICTED_BUILTINS
        assert "format" in RESTRICTED_BUILTINS

    def test_allows_type_checking(self):
        assert "isinstance" in RESTRICTED_BUILTINS
        assert "issubclass" in RESTRICTED_BUILTINS
        assert "type" in RESTRICTED_BUILTINS
        assert "callable" in RESTRICTED_BUILTINS

    def test_allows_collection_operations(self):
        assert "len" in RESTRICTED_BUILTINS
        assert "all" in RESTRICTED_BUILTINS
        assert "any" in RESTRICTED_BUILTINS
        assert "iter" in RESTRICTED_BUILTINS
        assert "next" in RESTRICTED_BUILTINS

    def test_allows_singletons(self):
        assert RESTRICTED_BUILTINS["True"] is True
        assert RESTRICTED_BUILTINS["False"] is False
        assert RESTRICTED_BUILTINS["None"] is None

    def test_dangerous_builtins_are_absent(self):
        forbidden = {"__import__", "open", "eval", "exec", "compile", "getattr",
                     "setattr", "hasattr", "super", "breakpoint", "input", "memoryview"}
        for name in forbidden:
            assert name not in RESTRICTED_BUILTINS, f"{name} should not be in restricted builtins"


class TestSafeEval:
    def test_simple_arithmetic(self):
        assert safe_eval("2 + 2") == 4
        assert safe_eval("10 * 5") == 50
        assert safe_eval("100 / 3") == 100 / 3

    def test_string_expression(self):
        assert safe_eval("'hello'.upper()") == "HELLO"

    def test_list_comprehension(self):
        assert safe_eval("[x * 2 for x in range(3)]") == [0, 2, 4]

    def test_builtin_functions(self):
        assert safe_eval("abs(-5)") == 5
        assert safe_eval("max(1, 2, 3)") == 3
        assert safe_eval("len('hello')") == 5
        assert safe_eval("bool(0)") is False

    def test_import_is_blocked(self):
        with pytest.raises(Exception):
            safe_eval("__import__('os')")

    def test_open_is_blocked(self):
        with pytest.raises(Exception):
            safe_eval("open('/etc/passwd')")

    def test_with_extra_globals(self):
        result = safe_eval("x + y", extra_globals={"x": 10, "y": 5})
        assert result == 15

    def test_with_local_ns(self):
        result = safe_eval("a + b", local_ns={"a": 1, "b": 2})
        assert result == 3

    def test_extra_globals_override_builtins(self):
        result = safe_eval("x", extra_globals={"x": "custom"})
        assert result == "custom"

    def test_complex_with_datetime(self):
        import datetime
        result = safe_eval(
            "datetime.datetime(2023, 1, 1)",
            extra_globals={"datetime": datetime},
        )
        assert result == datetime.datetime(2023, 1, 1)

    def test_comparison(self):
        assert safe_eval("5 > 3") is True
        assert safe_eval("5 < 3") is False

    def test_logical_operators(self):
        assert safe_eval("True and False") is False
        assert safe_eval("True or False") is True
        assert safe_eval("not False") is True

    def test_set_operations(self):
        assert safe_eval("{1, 2, 3} & {2, 3, 4}") == {2, 3}


class TestSafeExec:
    def test_executes_simple_code(self):
        ns = safe_exec("x = 42")
        assert ns["x"] == 42

    def test_executes_multiple_statements(self):
        ns = safe_exec("a = 1\nb = a + 2")
        assert ns["a"] == 1
        assert ns["b"] == 3

    def test_defines_function(self):
        ns = safe_exec("def add(a, b):\n    return a + b")
        assert "add" in ns
        assert ns["add"](3, 4) == 7

    def test_with_extra_globals(self):
        ns = safe_exec("z = x + y", extra_globals={"x": 10, "y": 20})
        assert ns["z"] == 30

    def test_with_local_ns(self):
        local = {"base": 100}
        ns = safe_exec("result = base * 2", local_ns=local)
        assert ns["result"] == 200
        assert ns is local

    def test_import_is_blocked(self):
        with pytest.raises(Exception):
            safe_exec("import os")

    def test_evil_code_is_blocked(self):
        with pytest.raises(Exception):
            safe_exec("__import__('os').system('rm -rf /')")

    def test_returns_local_namespace(self):
        ns = safe_exec("a = 1\nb = 2")
        assert isinstance(ns, dict)
        assert set(ns.keys()) >= {"a", "b"}

    def test_class_definition(self):
        ns = safe_exec("class Foo:\n    value = 42")
        assert "Foo" in ns
        assert ns["Foo"].value == 42

    def test_del_statement(self):
        local = {"x": 10}
        ns = safe_exec("del x", local_ns=local)
        assert "x" not in ns

    def test_for_loop(self):
        ns = safe_exec("total = 0\nfor i in range(5):\n    total += i")
        assert ns["total"] == 10


class TestEvalResult:
    def test_namedtuple_creation(self):
        result = EvalResult("value", None)
        assert result.value == "value"
        assert result.error is None

    def test_namedtuple_with_error(self):
        err = ValueError("test")
        result = EvalResult(None, err)
        assert result.value is None
        assert result.error is err
