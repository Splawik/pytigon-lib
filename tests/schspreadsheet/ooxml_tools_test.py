from pytigon_lib.schspreadsheet.ooxml_tools import *
from lxml import etree

# Pytest tests
import pytest
from unittest.mock import MagicMock


def test_make_update_filter_fun():
    doc_transform = MagicMock()
    doc_transform.get_xml_content.return_value = {
        "data": etree.Element("root"),
        "from_cache": False,
    }
    doc_transform.to_update = []

    root = etree.Element("root")
    cache_fields = etree.SubElement(root, "cacheFields")
    cache_field = etree.SubElement(cache_fields, "cacheField", name="test_field")
    shared_items = etree.SubElement(cache_field, "sharedItems")
    etree.SubElement(shared_items, "item", v="value1")
    etree.SubElement(shared_items, "item", v="value2")

    update_filter = make_update_filter_fun(
        "test_field", "pivot_table", "pivot_field", "value1"
    )
    result = update_filter(doc_transform, root)

    assert result is False
    assert len(doc_transform.to_update) == 1


def test_make_group_fun():
    doc_transform = MagicMock()
    root = etree.Element("root")
    pivot_fields = etree.SubElement(root, "pivotFields")
    pivot_field = etree.SubElement(pivot_fields, "pivotField")
    etree.SubElement(pivot_field, "item", n="value1")
    etree.SubElement(pivot_field, "item", n="value2")

    update_group = make_group_fun(0, "value1")
    result = update_group(doc_transform, root)

    assert result is True
    items = pivot_field.findall(".//item")
    assert items[0].attrib.get("sd") is None
    assert items[1].attrib.get("sd") == "0"


if __name__ == "__main__":
    pytest.main()
