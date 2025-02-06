from pytigon_lib.schtools.schjson import *

# Pytest tests
import pytest


def test_complex_encoder():
    """Test the ComplexEncoder with various types."""
    encoder = ComplexEncoder()
    assert encoder.default(datetime.datetime(2023, 1, 1)) == {
        "object": "datetime.datetime(2023, 1, 1, 0, 0)"
    }
    assert encoder.default(Decimal("10.5")) == {"object": "Decimal('10.5')"}


def test_dumps_loads():
    """Test the dumps and loads functions."""
    data = {"date": datetime.datetime(2023, 1, 1), "value": Decimal("10.5")}
    encoded = dumps(data)
    decoded = loads(encoded)
    assert decoded["date"] == data["date"]
    assert decoded["value"] == data["value"]


def test_json_dumps_loads():
    """Test the json_dumps and json_loads functions."""
    data = {"date": datetime.datetime(2023, 1, 1), "value": Decimal("10.5")}
    encoded = json_dumps(data)
    decoded = json_loads(encoded)
    assert decoded["date"] == data["date"]
    assert decoded["value"] == data["value"]


def test_complex_decoder():
    """Test the ComplexDecoder."""
    decoder = ComplexDecoder()
    data = '{"date": {"object": "datetime.datetime(2023, 1, 1, 0, 0)"}, "value": {"object": "Decimal(\'10.5\')"}}'
    decoded = decoder.decode(data)
    assert decoded["date"] == datetime.datetime(2023, 1, 1)
    assert decoded["value"] == Decimal("10.5")


if __name__ == "__main__":
    pytest.main()
