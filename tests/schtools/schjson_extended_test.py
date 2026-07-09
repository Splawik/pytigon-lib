"""Tests for :mod:`pytigon_lib.schtools.schjson` extended."""
import datetime
import json
from decimal import Decimal

import pytest

from pytigon_lib.schtools.schjson import ComplexDecoder, ComplexEncoder, dumps, json_dumps, json_loads, loads


class TestComplexEncoderAdditional:
    @pytest.fixture
    def encoder(self):
        return ComplexEncoder()

    def test_date(self, encoder):
        result = encoder.default(datetime.date(2024, 12, 31))
        assert result == {"object": "datetime.date(2024, 12, 31)"}

    def test_datetime_with_tzinfo(self, encoder):
        dt = datetime.datetime(2023, 1, 1)
        result = encoder.default(dt)
        assert "object" in result

    def test_decimal_negative(self, encoder):
        result = encoder.default(Decimal("-10.5"))
        assert result == {"object": "Decimal('-10.5')"}

    def test_decimal_zero(self, encoder):
        result = encoder.default(Decimal("0"))
        assert result == {"object": "Decimal('0')"}


class TestDumpsLoadsExtra:
    def test_dumps_simple_list(self):
        data = [1, 2, 3]
        decoded = loads(dumps(data))
        assert decoded == data

    def test_dumps_none(self):
        assert loads(dumps(None)) is None

    def test_dumps_bool(self):
        assert loads(dumps(True)) is True

    def test_dumps_nested(self):
        data = {"a": {"b": {"c": [1, 2, 3]}}}
        assert loads(dumps(data)) == data

    def test_dumps_empty_dict(self):
        assert loads(dumps({})) == {}

    def test_dumps_empty_list(self):
        assert loads(dumps([])) == []


class TestJsonDumpsLoadsExtra:
    def test_json_dumps_none(self):
        assert json_loads(json_dumps(None)) is None

    def test_json_dumps_bool(self):
        assert json_loads(json_dumps(True)) is True
        assert json_loads(json_dumps(False)) is False

    def test_json_dumps_int(self):
        assert json_loads(json_dumps(42)) == 42

    def test_json_dumps_float(self):
        assert json_loads(json_dumps(3.14)) == 3.14

    def test_json_dumps_string(self):
        assert json_loads(json_dumps("hello")) == "hello"

    def test_json_dumps_list(self):
        data = [1, "two", 3.0]
        assert json_loads(json_dumps(data)) == data

    def test_json_dumps_indent_none(self):
        assert json_loads(json_dumps({"a": 1}, indent=4)) == {"a": 1}


class TestComplexDecoderExtra:
    def test_decode_simple(self):
        decoder = ComplexDecoder()
        assert decoder.decode("42") == 42
        assert decoder.decode('"hello"') == "hello"
        assert decoder.decode("[1, 2, 3]") == [1, 2, 3]

    def test_decode_true_false(self):
        decoder = ComplexDecoder()
        assert decoder.decode("true") is True
        assert decoder.decode("false") is False
        assert decoder.decode("null") is None
