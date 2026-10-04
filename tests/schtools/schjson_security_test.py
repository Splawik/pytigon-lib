"""Security regression tests for :mod:`pytigon_lib.schtools.schjson`.

The historical ``{"object": "<repr>"}`` envelope was decoded with ``eval()``.
The validator in ``safe_exec`` blocked attribute names such as ``__class__`` but
not ``globals()`` nor string subscripts, so a JSON payload could reach the real
builtins and execute code::

    {"object": "globals()['__builtins__'].__import__('os').system('...')"}

These tests lock in the fix: decoding must never evaluate Python source, while
legitimate ``datetime``/``date``/``Decimal`` values still round-trip.
"""

import datetime
import json
from decimal import Decimal

import pytest

from pytigon_lib.schtools import schjson
from pytigon_lib.schtools.schjson import (
    ComplexDecoder,
    ComplexEncoder,
    as_complex,
    json_dumps,
    json_loads,
    loads,
)

# Payloads that previously produced code execution or interpreter access.
MALICIOUS_ENVELOPES = [
    "__import__('os').system('echo pwn')",
    "globals()['__builtins__']",
    "globals()['__builtins__'].__import__('os').system('echo pwn')",
    "globals()['__builtins__'].open('/etc/passwd').read()",
    "open('/etc/passwd').read()",
    "open('/tmp/pwn', 'w').write('x')",
    "()." + "class" + ".__base__.__subclasses__()",
    "().__class__.__base__.__subclasses__()",
    "getattr(0, '__class__')",
    "getattr(0, '__cl' + 'ass__')",
    "compile('1', '<x>', 'eval')",
    "eval('1+1')",
    "exec('x = 1')",
    "vars()",
    "locals()",
    "builtins",
    "1 + 1",
    "[x for x in (1, 2)]",
]


class TestNoCodeExecution:
    """A decoded ``object`` envelope must never execute or expose internals."""

    @pytest.mark.parametrize("payload", MALICIOUS_ENVELOPES)
    def test_legacy_object_envelope_is_not_executed(self, payload):
        assert as_complex({"object": payload}) is None

    @pytest.mark.parametrize("payload", MALICIOUS_ENVELOPES)
    def test_json_loads_is_not_executed(self, payload):
        encoded = json.dumps({"object": payload})
        assert json_loads(encoded) is None

    @pytest.mark.parametrize("payload", MALICIOUS_ENVELOPES)
    def test_url_loads_is_not_executed(self, payload):
        encoded = schjson.dumps({"object": payload})
        assert loads(encoded) is None

    @pytest.mark.parametrize("payload", MALICIOUS_ENVELOPES)
    def test_complex_decoder_is_not_executed(self, payload):
        encoded = json.dumps({"object": payload})
        assert ComplexDecoder().decode(encoded) is None

    def test_dangerous_subscript_is_rejected(self):
        """The specific bypass: globals()[...] then attribute access."""
        payload = "globals()['__builtins__'].__import__('os').system('id')"
        assert as_complex({"object": payload}) is None


class TestLegitimateValuesStillWork:
    """The fix must not break the values the framework actually stores."""

    def test_legacy_datetime_still_decodes(self):
        dct = {"object": "datetime.datetime(2023, 1, 1, 12, 30, 45)"}
        assert as_complex(dct) == datetime.datetime(2023, 1, 1, 12, 30, 45)

    def test_legacy_date_still_decodes(self):
        assert as_complex({"object": "datetime.date(2023, 1, 1)"}) == datetime.date(2023, 1, 1)

    def test_legacy_decimal_still_decodes(self):
        assert as_complex({"object": "Decimal('10.5')"}) == Decimal("10.5")

    def test_legacy_time_and_timedelta_still_decode(self):
        assert as_complex({"object": "datetime.time(1, 2, 3)"}) == datetime.time(1, 2, 3)
        assert as_complex({"object": "datetime.timedelta(1, 2)"}) == datetime.timedelta(1, 2)

    def test_typed_envelope_roundtrip(self):
        data = {
            "ts": datetime.datetime(2023, 6, 15, 10, 20, 30, 400000),
            "d": datetime.date(2023, 6, 15),
            "amount": Decimal("123.45"),
            "name": "x",
            "n": 7,
        }
        assert loads(schjson.dumps(data)) == data
        assert json_loads(json_dumps(data)) == data

    def test_encoder_never_emits_eval_envelope_for_datetime(self):
        encoded = json.dumps({"ts": datetime.datetime(2023, 1, 1)}, cls=ComplexEncoder)
        assert '"object"' not in encoded
        assert '"__pytigon_type__": "datetime"' in encoded


class TestNoEvalInModule:
    """Guard against a future change reintroducing ``eval`` into the JSON path."""

    def test_module_does_not_import_safe_eval(self):
        assert not hasattr(schjson, "_safe_eval")

    def test_module_does_not_define_safe_eval_globals(self):
        assert not hasattr(schjson, "_SAFE_EVAL_GLOBALS")

    def test_no_eval_call_in_source(self):
        import ast
        import inspect

        tree = ast.parse(inspect.getsource(schjson))
        dangerous_calls = [
            node.func.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id in {"eval", "exec", "compile", "__import__"}
        ]
        assert dangerous_calls == []

    def test_object_key_alone_does_not_imply_code_execution(self):
        """The only way from data to code is gone; unknown types survive as data."""
        result = as_complex({"object": "MyClass(1, 2)"})
        assert result is None
