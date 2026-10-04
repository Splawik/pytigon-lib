"""Tests for :mod:`pytigon_lib.schtools.schjson`."""

import datetime
import json
from decimal import Decimal

import pytest

from pytigon_lib.schtools.schjson import (
    _ENVELOPE_TYPE_KEY,
    _STANDARD_TYPES,
    ComplexDecoder,
    ComplexEncoder,
    as_complex,
    dumps,
    json_dumps,
    json_loads,
    loads,
)

# ============================================================================
# ComplexEncoder
# ============================================================================


class TestComplexEncoder:
    """Tests for :class:`ComplexEncoder`."""

    @pytest.fixture
    def encoder(self):
        return ComplexEncoder()

    # -- datetime -----------------------------------------------------------

    def test_datetime(self, encoder):
        result = encoder.default(datetime.datetime(2023, 1, 1))
        assert result == {
            "__pytigon_type__": "datetime",
            "value": "2023-01-01T00:00:00",
        }

    def test_datetime_with_microseconds(self, encoder):
        result = encoder.default(datetime.datetime(2023, 1, 1, 12, 30, 45, 123456))
        assert result == {
            "__pytigon_type__": "datetime",
            "value": "2023-01-01T12:30:45.123456",
        }

    def test_datetime_zero_seconds_are_kept(self, encoder):
        result = encoder.default(datetime.datetime(2023, 1, 1, 12, 0, 0))
        assert result == {
            "__pytigon_type__": "datetime",
            "value": "2023-01-01T12:00:00",
        }

    def test_datetime_timezone_is_preserved(self, encoder):
        dt = datetime.datetime(2023, 1, 1, tzinfo=datetime.UTC)
        result = encoder.default(dt)
        assert result["__pytigon_type__"] == "datetime"
        assert result["value"] == "2023-01-01T00:00:00+00:00"

    # -- date ---------------------------------------------------------------

    def test_date(self, encoder):
        result = encoder.default(datetime.date(2023, 1, 1))
        assert result == {"__pytigon_type__": "date", "value": "2023-01-01"}

    # -- Decimal ------------------------------------------------------------

    def test_decimal(self, encoder):
        result = encoder.default(Decimal("10.5"))
        assert result == {"__pytigon_type__": "decimal", "value": "10.5"}

    def test_decimal_integer(self, encoder):
        result = encoder.default(Decimal("42"))
        assert result == {"__pytigon_type__": "decimal", "value": "42"}

    # -- numpy arrays (simulated via tolist) --------------------------------

    def test_object_with_tolist(self, encoder):
        """Any object with a ``tolist()`` method uses that for serialization."""

        class FakeArray:
            def tolist(self):
                return [1, 2, 3]

        result = encoder.default(FakeArray())
        assert result == [1, 2, 3]

    # -- unknown complex types ----------------------------------------------

    def test_unknown_complex_type(self, encoder):
        """Types without special handling fall back to an informational repr."""

        class MyCustomType:
            pass

        obj = MyCustomType()
        result = encoder.default(obj)
        assert result == {"object": repr(obj)}

    # -- standard types pass through to parent ------------------------------

    def test_string_passes_through(self, encoder):
        """Strings are handled by the parent encoder."""
        with pytest.raises(TypeError):
            encoder.default("hello")

    def test_int_passes_through(self, encoder):
        with pytest.raises(TypeError):
            encoder.default(42)

    def test_list_passes_through(self, encoder):
        with pytest.raises(TypeError):
            encoder.default([1, 2, 3])

    # -- integration: json.dumps with ComplexEncoder ------------------------

    def test_json_dumps_datetime(self):
        data = {"ts": datetime.datetime(2023, 1, 1, 12, 0, 0)}
        encoded = json.dumps(data, cls=ComplexEncoder)
        assert "2023-01-01T12:00:00" in encoded
        assert '"__pytigon_type__": "datetime"' in encoded

    def test_json_dumps_decimal(self):
        data = {"price": Decimal("19.99")}
        encoded = json.dumps(data, cls=ComplexEncoder)
        assert '"__pytigon_type__": "decimal"' in encoded
        assert "19.99" in encoded

    def test_json_dumps_unknown_type_falls_back_to_repr(self):
        """Unknown types become ``{"object": "..."}`` via repr fallback."""

        class Unknown:
            pass

        obj = Unknown()
        data = {"item": obj}
        encoded = json.dumps(data, cls=ComplexEncoder)
        assert repr(obj) in encoded


# ============================================================================
# as_complex
# ============================================================================


class TestAsComplex:
    """Tests for :func:`as_complex`."""

    # -- typed envelope (new format) ----------------------------------------

    def test_decodes_typed_datetime(self):
        dct = {"__pytigon_type__": "datetime", "value": "2023-01-01T00:00:00"}
        assert as_complex(dct) == datetime.datetime(2023, 1, 1)

    def test_decodes_typed_date(self):
        dct = {"__pytigon_type__": "date", "value": "2023-01-01"}
        assert as_complex(dct) == datetime.date(2023, 1, 1)

    def test_decodes_typed_decimal(self):
        dct = {"__pytigon_type__": "decimal", "value": "10.5"}
        assert as_complex(dct) == Decimal("10.5")

    def test_malformed_typed_datetime_is_returned_unchanged(self):
        dct = {"__pytigon_type__": "datetime", "value": "not-a-date"}
        assert as_complex(dct) is dct

    def test_unknown_typed_envelope_is_returned_unchanged(self):
        dct = {"__pytigon_type__": "whatever", "value": "x"}
        assert as_complex(dct) is dct

    # -- legacy ``{"object": ...}`` envelope, read without eval -------------

    def test_decodes_legacy_datetime(self):
        dct = {"object": "datetime.datetime(2023, 1, 1, 0, 0)"}
        result = as_complex(dct)
        assert result == datetime.datetime(2023, 1, 1)

    def test_decodes_legacy_date(self):
        dct = {"object": "datetime.date(2023, 1, 1)"}
        result = as_complex(dct)
        assert result == datetime.date(2023, 1, 1)

    def test_decodes_legacy_decimal(self):
        dct = {"object": "Decimal('10.5')"}
        result = as_complex(dct)
        assert result == Decimal("10.5")

    def test_decodes_legacy_microseconds_and_negative_numbers(self):
        dct = {"object": "datetime.datetime(2023, 1, 1, 12, 30, 45, 123456)"}
        assert as_complex(dct) == datetime.datetime(2023, 1, 1, 12, 30, 45, 123456)

        dct = {"object": "Decimal('-10.5')"}
        assert as_complex(dct) == Decimal("-10.5")

    def test_decodes_standard_type_via_repr(self):
        """Plain literals whose repr is valid Python are recovered."""
        assert as_complex({"object": "42"}) == 42
        assert as_complex({"object": "3.14"}) == 3.14
        assert as_complex({"object": "'hello'"}) == "hello"
        assert as_complex({"object": "[1, 2, 3]"}) == [1, 2, 3]
        assert as_complex({"object": "{'a': 1}"}) == {"a": 1}
        assert as_complex({"object": "True"}) is True
        assert as_complex({"object": "None"}) is None

    def test_no_object_key_returns_dict(self):
        dct = {"some_key": "some_value"}
        assert as_complex(dct) is dct

    def test_invalid_repr_returns_none(self):
        """Invalid Python expressions return None silently."""
        dct = {"object": "this is not valid python !!!"}
        assert as_complex(dct) is None

    def test_empty_object_value_returns_none(self):
        dct = {"object": ""}
        assert as_complex(dct) is None


# ============================================================================
# dumps / loads  (URL-safe round-trip)
# ============================================================================


class TestDumpsLoads:
    """Round-trip tests for :func:`dumps` and :func:`loads`."""

    def test_roundtrip_datetime(self):
        data = {"date": datetime.datetime(2023, 1, 1)}
        decoded = loads(dumps(data))
        assert decoded["date"] == data["date"]

    def test_roundtrip_datetime_microseconds(self):
        data = {"date": datetime.datetime(2023, 1, 1, 12, 30, 45, 123456)}
        decoded = loads(dumps(data))
        assert decoded["date"] == data["date"]

    def test_roundtrip_datetime_timezone(self):
        data = {"date": datetime.datetime(2023, 1, 1, tzinfo=datetime.UTC)}
        decoded = loads(dumps(data))
        assert decoded["date"] == data["date"]
        assert decoded["date"].tzinfo is not None

    def test_roundtrip_date(self):
        data = {"date": datetime.date(2023, 6, 15)}
        decoded = loads(dumps(data))
        assert decoded["date"] == data["date"]

    def test_roundtrip_decimal(self):
        data = {"value": Decimal("10.5")}
        decoded = loads(dumps(data))
        assert decoded["value"] == data["value"]

    def test_roundtrip_mixed(self):
        data = {
            "date": datetime.datetime(2023, 1, 1),
            "value": Decimal("10.5"),
            "name": "test",
            "count": 42,
        }
        decoded = loads(dumps(data))
        assert decoded == data

    def test_roundtrip_plain(self):
        """Plain JSON types round-trip correctly."""
        data = {"a": 1, "b": [1, 2, 3], "c": None, "d": True}
        decoded = loads(dumps(data))
        assert decoded == data

    def test_dumps_is_url_encoded(self):
        """The output of dumps() must be URL-safe."""
        data = {"x": "hello world"}
        encoded = dumps(data)
        assert "+" in encoded or "%20" in encoded
        decoded = loads(encoded)
        assert decoded == data

    def test_loads_invalid_raises_valueerror(self):
        with pytest.raises(ValueError):
            loads("not valid json {{{")


# ============================================================================
# json_dumps / json_loads  (plain JSON round-trip)
# ============================================================================


class TestJsonDumpsLoads:
    """Round-trip tests for :func:`json_dumps` and :func:`json_loads`."""

    def test_roundtrip_datetime(self):
        data = {"date": datetime.datetime(2023, 1, 1)}
        decoded = json_loads(json_dumps(data))
        assert decoded["date"] == data["date"]

    def test_roundtrip_date(self):
        data = {"date": datetime.date(2023, 6, 15)}
        decoded = json_loads(json_dumps(data))
        assert decoded["date"] == data["date"]

    def test_roundtrip_decimal(self):
        data = {"value": Decimal("10.5")}
        decoded = json_loads(json_dumps(data))
        assert decoded["value"] == data["value"]

    def test_roundtrip_mixed(self):
        data = {
            "date": datetime.datetime(2023, 1, 1),
            "value": Decimal("10.5"),
            "name": "test",
            "count": 42,
        }
        decoded = json_loads(json_dumps(data))
        assert decoded == data

    def test_roundtrip_plain(self):
        data = {"a": 1, "b": [1, 2, 3], "c": None, "d": True}
        decoded = json_loads(json_dumps(data))
        assert decoded == data

    def test_indent_parameter(self):
        """json_dumps with indent produces pretty-printed output."""
        data = {"a": 1}
        encoded = json_dumps(data, indent=2)
        assert "\n" in encoded
        assert json_loads(encoded) == data

    def test_json_loads_invalid_raises_valueerror(self):
        with pytest.raises(ValueError):
            json_loads("not valid json {{{")


# ============================================================================
# ComplexDecoder
# ============================================================================


class TestComplexDecoder:
    """Tests for :class:`ComplexDecoder`."""

    def test_decode_typed_datetime(self):
        decoder = ComplexDecoder()
        data = '{"date": {"__pytigon_type__": "datetime", "value": "2023-01-01T00:00:00"}}'
        decoded = decoder.decode(data)
        assert decoded["date"] == datetime.datetime(2023, 1, 1)

    def test_decode_legacy_datetime(self):
        decoder = ComplexDecoder()
        data = '{"date": {"object": "datetime.datetime(2023, 1, 1, 0, 0)"}}'
        decoded = decoder.decode(data)
        assert decoded["date"] == datetime.datetime(2023, 1, 1)

    def test_decode_decimal(self):
        decoder = ComplexDecoder()
        data = '{"value": {"__pytigon_type__": "decimal", "value": "10.5"}}'
        decoded = decoder.decode(data)
        assert decoded["value"] == Decimal("10.5")

    def test_decode_mixed(self):
        decoder = ComplexDecoder()
        data = (
            '{"date": {"__pytigon_type__": "datetime", "value": "2023-01-01T00:00:00"}, '
            '"value": {"object": "Decimal(\'10.5\')"}}'
        )
        decoded = decoder.decode(data)
        assert decoded["date"] == datetime.datetime(2023, 1, 1)
        assert decoded["value"] == Decimal("10.5")

    def test_decode_plain_json(self):
        decoder = ComplexDecoder()
        data = '{"a": 1, "b": "hello"}'
        decoded = decoder.decode(data)
        assert decoded == {"a": 1, "b": "hello"}


# ============================================================================
# Constants
# ============================================================================


class TestConstants:
    """Sanity checks for module-level constants."""

    def test_standard_types_contains_expected(self):
        assert "str" in _STANDARD_TYPES
        assert "int" in _STANDARD_TYPES
        assert "float" in _STANDARD_TYPES
        assert "bool" in _STANDARD_TYPES
        assert "NoneType" in _STANDARD_TYPES

    def test_typed_envelope_key_is_namespaced(self):
        assert _ENVELOPE_TYPE_KEY == "__pytigon_type__"
