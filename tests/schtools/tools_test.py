from pytigon_lib.schtools.tools import *

# Pytest tests
import pytest


def test_split2():
    assert split2("hello world", " ") == ("hello", "world")
    assert split2("hello world", "x") == ("hello world", "")
    assert split2("", " ") == ("", "")


def test_bencode_bdecode():
    original = "hello"
    encoded = bencode(original)
    decoded = bdecode(encoded)
    assert decoded == original


def test_clean_href():
    assert clean_href("  http://example.com\n") == "http://example.com"


def test_is_null():
    assert is_null(None, "default") == "default"
    assert is_null("value", "default") == "value"


def test_norm_indent():
    text = "  line1\n  line2\n    line3"
    expected = "line1\nline2\n  line3"
    assert norm_indent(text) == expected


def test_update_nested_dict():
    d = {"a": {"b": 1}}
    u = {"a": {"c": 2}}
    update_nested_dict(d, u)
    assert d == {"a": {"b": 1, "c": 2}}


if __name__ == "__main__":
    pytest.main()
