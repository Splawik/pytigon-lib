"""Tests for :mod:`pytigon_lib.schspreadsheet.ooxml_tools`."""
from unittest.mock import MagicMock

import pytest

from pytigon_lib.schspreadsheet.ooxml_tools import make_update_filter_fun, make_group_fun


class TestMakeUpdateFilterFun:
    def test_returns_callable(self):
        fun = make_update_filter_fun("field_name", "pivot_table", "pivot_field", "value")
        assert callable(fun)

    def test_callable_signature(self):
        fun = make_update_filter_fun("f", "pt", "pf", "v")
        mock_transform = MagicMock()
        mock_transform.get_xml_content.return_value = {
            "data": type("MockXml", (), {"nsmap": {}, "findall": lambda *a, **kw: []})(),
            "from_cache": True,
        }
        mock_root = type("MockRoot", (), {
            "nsmap": {},
            "findall": lambda *a, **kw: [],
        })()
        result = fun(mock_transform, mock_root)
        assert result is False

    def test_empty_fields(self):
        fun = make_update_filter_fun("nonexistent", "pt", "pf", "v")
        mock_transform = MagicMock()
        mock_transform.get_xml_content.return_value = {
            "data": type("MockXml", (), {"nsmap": {}, "findall": lambda *a, **kw: []})(),
            "from_cache": True,
        }
        mock_root = type("MockRoot", (), {
            "nsmap": {},
            "findall": lambda *a, **kw: [],
        })()
        result = fun(mock_transform, mock_root)
        assert result is False


class TestMakeGroupFun:
    def test_returns_callable(self):
        fun = make_group_fun(0, "val1;val2")
        assert callable(fun)

    def test_callable_empty_fields(self):
        fun = make_group_fun(0, "a;b")
        mock_transform = MagicMock()
        mock_root = type("MockRoot", (), {
            "nsmap": {},
            "findall": lambda *a, **kw: [],
        })()
        with pytest.raises(RuntimeError):
            fun(mock_transform, mock_root)

    def test_callable_with_items(self):
        fun = make_group_fun(0, "show")

        class MockItem:
            tag = "item"

            def __init__(self, attrib):
                self.attrib = attrib

        class MockField:
            tag = "field"

            def findall(self, *a, **kw):
                return [
                    MockItem({"n": "show"}),
                    MockItem({"n": "hide"}),
                ]

        class MockRoot:
            nsmap = {}

            def findall(self, *a, **kw):
                return [MockField()]

        mock_transform = MagicMock()
        mock_root = MockRoot()
        result = fun(mock_transform, mock_root)
        assert result is True
