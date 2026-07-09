"""Extra tests for :mod:`pytigon_lib.schspreadsheet.ooxml_tools`."""
from unittest.mock import MagicMock

import pytest
from lxml import etree

from pytigon_lib.schspreadsheet.ooxml_tools import make_group_fun, make_update_filter_fun


class TestMakeUpdateFilterFunExtra:
    def test_returns_callable(self):
        fun = make_update_filter_fun("f", "pt", "pf", "val")
        assert callable(fun)

    def test_from_cache_skips_update_list(self):
        doc_transform = MagicMock()
        doc_transform.get_xml_content.return_value = {
            "data": etree.Element("root"),
            "from_cache": True,
        }
        doc_transform.to_update = []

        root = etree.Element("root")
        cache_fields = etree.SubElement(root, "cacheFields")
        cache_field = etree.SubElement(cache_fields, "cacheField", name="test")
        shared_items = etree.SubElement(cache_field, "sharedItems")
        etree.SubElement(shared_items, "item", v="val1")

        fun = make_update_filter_fun("test", "pt", "pf", "val1")
        result = fun(doc_transform, root)
        assert result is False
        assert len(doc_transform.to_update) == 0

    def test_value_not_found(self):
        doc_transform = MagicMock()
        doc_transform.get_xml_content.return_value = {
            "data": etree.Element("root"),
            "from_cache": True,
        }
        doc_transform.to_update = []

        root = etree.Element("root")
        cache_fields = etree.SubElement(root, "cacheFields")
        cache_field = etree.SubElement(cache_fields, "cacheField", name="test")
        shared_items = etree.SubElement(cache_field, "sharedItems")
        etree.SubElement(shared_items, "item", v="val1")

        fun = make_update_filter_fun("test", "pt", "pf", "not_found")
        result = fun(doc_transform, root)
        assert result is False

    def test_empty_cache_fields(self):
        doc_transform = MagicMock()
        doc_transform.get_xml_content.return_value = {
            "data": etree.Element("root"),
            "from_cache": True,
        }
        doc_transform.to_update = []

        root = etree.Element("root")

        fun = make_update_filter_fun("test", "pt", "pf", "val")
        result = fun(doc_transform, root)
        assert result is False

    def test_matching_value_updates_item(self):
        doc_transform = MagicMock()
        mock_root2 = etree.Element("root")
        pivot_fields = etree.SubElement(mock_root2, "pivotFields")
        pivot_field = etree.SubElement(pivot_fields, "pivotField", name="pf")
        items = etree.SubElement(pivot_field, "items")
        etree.SubElement(items, "item", x="0")
        etree.SubElement(items, "item", x="1", h="1")

        doc_transform.get_xml_content.return_value = {
            "data": mock_root2,
            "from_cache": False,
        }
        doc_transform.to_update = []

        root = etree.Element("root")
        cache_fields = etree.SubElement(root, "cacheFields")
        cache_field = etree.SubElement(cache_fields, "cacheField", name="f")
        shared_items = etree.SubElement(cache_field, "sharedItems")
        etree.SubElement(shared_items, "item", v="a")
        etree.SubElement(shared_items, "item", v="b")

        fun = make_update_filter_fun("f", "pt", "pf", "b")
        result = fun(doc_transform, root)
        assert result is False


class TestMakeGroupFunExtra:
    def test_returns_callable(self):
        fun = make_group_fun(0, "a;b;c")
        assert callable(fun)

    def test_shows_matching_items(self):
        doc_transform = MagicMock()
        root = etree.Element("root")
        pivot_fields = etree.SubElement(root, "pivotFields")
        pivot_field = etree.SubElement(pivot_fields, "pivotField")
        etree.SubElement(pivot_field, "item", n="show")
        etree.SubElement(pivot_field, "item", n="hide")

        fun = make_group_fun(0, "show")
        result = fun(doc_transform, root)
        assert result is True

    def test_empty_values_on(self):
        doc_transform = MagicMock()
        root = etree.Element("root")
        pivot_fields = etree.SubElement(root, "pivotFields")
        pivot_field = etree.SubElement(pivot_fields, "pivotField")
        etree.SubElement(pivot_field, "item", n="item1")

        fun = make_group_fun(0, "")
        result = fun(doc_transform, root)
        assert result is True

    def test_multiple_matches(self):
        doc_transform = MagicMock()
        root = etree.Element("root")
        pivot_fields = etree.SubElement(root, "pivotFields")
        pivot_field = etree.SubElement(pivot_fields, "pivotField")
        etree.SubElement(pivot_field, "item", n="one")
        etree.SubElement(pivot_field, "item", n="two")
        etree.SubElement(pivot_field, "item", n="three")

        fun = make_group_fun(0, "one;three")
        result = fun(doc_transform, root)
        assert result is True

    def test_field_index_out_of_range_raises(self):
        doc_transform = MagicMock()
        root = etree.Element("root")
        pivot_fields = etree.SubElement(root, "pivotFields")
        pivot_field = etree.SubElement(pivot_fields, "pivotField")
        etree.SubElement(pivot_field, "item", n="x")

        fun = make_group_fun(1, "x")
        with pytest.raises(RuntimeError):
            fun(doc_transform, root)
