"""Tests for :mod:`pytigon_lib.schtools.safe_exec`.

The policy under test is deliberately liberal - Pytigon runs its own project's
build scripts and code an administrator stored in the database, so imports and
I/O have to keep working. What is tested here is the one thing that is actually
enforced: the interpreter-introspection ladder that used to turn any evaluated
string into arbitrary code execution.
"""

import datetime
import decimal

import pytest

from pytigon_lib.schtools.safe_exec import (
    EvalResult,
    ForbiddenConstruct,
    safe_eval,
    safe_exec,
    validate_source,
)

# Every one of these reached os.system through the old implementation.
ESCAPES = [
    "().__class__.__base__.__subclasses__()",
    "().__class__.__bases__[0].__subclasses__()",
    "().__class__.__mro__",
    "type.__subclasses__()",
    "object.__subclasses__()",
    "().__class__.__init__.__globals__",
    "print.__globals__",
    "(lambda: 0).__globals__",
    "().__getattribute__('__class__')",
    "().__reduce__",
    "getattr((), '__class__')",
    "getattr((), '__cl' + 'ass__')",
    "getattr(print, name='__globals__')",
    "eval('1+1')",
    "exec('x=1')",
    "compile('1', 'f', 'eval')",
    "__import__('os')",
]


class TestEscapeBlocked:
    """The escape ladder must be refused."""

    @pytest.mark.parametrize("source", ESCAPES)
    def test_escape_is_blocked(self, source):
        with pytest.raises(ForbiddenConstruct):
            safe_eval(source)

    @pytest.mark.parametrize("source", ESCAPES)
    def test_escape_is_blocked_in_exec_too(self, source):
        with pytest.raises(ForbiddenConstruct):
            safe_exec(source)


class TestInterpreterReentry:
    def test_validate_source_rejects_statements_in_eval_mode(self):
        with pytest.raises(SyntaxError):
            validate_source("x = 1", mode="eval")

    def test_validate_source_accepts_statements_in_exec_mode(self):
        assert validate_source("x = 1", mode="exec") is not None


class TestLiberalUse:
    """Ordinary code must keep working - this is a local application."""

    def test_arithmetic(self):
        assert safe_eval("2 + 2") == 4
        assert safe_eval("10 * 5") == 50

    def test_schjson_roundtrip_datetime(self):
        assert safe_eval(
            "datetime.datetime(2024, 1, 1)",
            extra_globals={"datetime": datetime},
        ) == datetime.datetime(2024, 1, 1)

    def test_schjson_roundtrip_decimal(self):
        assert safe_eval(
            "Decimal('1.5')",
            extra_globals={"Decimal": decimal.Decimal},
        ) == decimal.Decimal("1.5")

    def test_comprehensions_generators_lambdas(self):
        assert safe_eval("[x * 2 for x in range(4)]") == [0, 2, 4, 6]
        assert safe_eval("sum(i * i for i in range(4))") == 14
        assert safe_eval("(lambda x: x + 1)(41)") == 42

    def test_ordinary_attribute_and_method_access(self):
        assert safe_eval("'abc'.upper()") == "ABC"
        assert safe_eval("','.join(['a', 'b'])") == "a,b"
        assert safe_eval("{'a': 1}.get('a')") == 1
        assert safe_eval("sorted({'b': 1, 'a': 2})") == ["a", "b"]

    def test_harmless_dunder_attributes_still_work(self):
        # Only the introspection ladder is refused, not dunders in general.
        assert safe_eval("[].__len__()") == 0
        assert safe_eval("'abc'.__contains__('b')") is True
        assert safe_eval("len('abc'.__doc__ or '') >= 0") is True

    def test_fstring(self):
        assert safe_eval("f'{1 + 1}'") == "2"

    def test_extra_globals_visible(self):
        assert safe_eval("value * 2", extra_globals={"value": 21}) == 42

    def test_local_namespace_visible(self):
        assert safe_eval("value + 1", local_ns={"value": 1}) == 2


class TestSafeExec:
    def test_imports_and_definitions_work(self):
        ns = safe_exec(
            "import os\n"
            "def build(prj=None):\n"
            "    return {'prj': prj, 'is_dir': os.path.isdir('/tmp')}\n"
            "class Thing:\n"
            "    def __init__(self, v):\n"
            "        self.v = v\n"
            "obj = Thing(5)\n",
            extra_globals={"os": __import__("os")},
        )
        assert ns["build"](prj="demo") == {"prj": "demo", "is_dir": True}
        assert ns["obj"].v == 5

    def test_file_access_works(self, tmp_path):
        target = tmp_path / "data.txt"
        target.write_text("hello", encoding="utf-8")
        ns = safe_exec(f"with open({str(target)!r}, encoding='utf-8') as f:\n    DATA = f.read()\n")
        assert ns["DATA"] == "hello"

    def test_returns_local_namespace(self):
        ns = safe_exec("A = 1\nB = A + 1\n")
        assert ns["A"] == 1
        assert ns["B"] == 2

    def test_extra_globals_reach_definitions(self):
        ns = safe_exec("def f():\n    return marker\n", extra_globals={"marker": 7})
        assert ns["f"]() == 7

    def test_syntax_error_propagates(self):
        with pytest.raises(SyntaxError):
            safe_exec("def broken(:")


class TestEvalResult:
    def test_named_tuple_shape_unchanged(self):
        r = EvalResult(value=1, error=None)
        assert r.value == 1
        assert r.error is None
        assert tuple(r) == (1, None)
