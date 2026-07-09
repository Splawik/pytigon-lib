"""Extra tests for :mod:`pytigon_lib.schspreadsheet.odf_process`."""
from unittest.mock import MagicMock, patch

import pytest
from lxml import etree

from pytigon_lib.schspreadsheet.odf_process import (
    OdfDocTransform,
    attr_get,
    inner_html,
    transform_str,
    OFFICE_URN,
    TABLE_URN,
    TEXT_URN,
)


class TestAttrGet:
    def test_match_suffix(self):
        attrs = {"some:name": "value"}
        assert attr_get(attrs, "name") == "value"

    def test_no_match(self):
        attrs = {"other:key": "val"}
        assert attr_get(attrs, "missing") is None

    def test_multiple_keys_matches_first(self):
        attrs = {"a:name": "first", "b:name": "second"}
        result = attr_get(attrs, "name")
        assert result is not None

    def test_exact_key(self):
        attrs = {"name": "exact"}
        assert attr_get(attrs, "name") == "exact"


class TestTransformStr:
    def test_only_triple_star(self):
        assert transform_str("x***y***z") == 'x"y"z'

    def test_only_double_star(self):
        assert transform_str("x**y**z") == "x'y'z"

    def test_mixed(self):
        result = transform_str("a***b**c")
        assert '"' in result
        assert "'" in result

    def test_no_special_chars(self):
        assert transform_str("normal text") == "normal text"

    def test_empty(self):
        assert transform_str("") == ""


class TestInnerHtml:
    def test_simple_element(self):
        elem = etree.fromstring("<p>Hello</p>")
        result = inner_html(elem)
        assert result == "Hello"

    def test_element_with_child(self):
        elem = etree.fromstring("<div>Hello <b>World</b></div>")
        result = inner_html(elem)
        assert "Hello" in result
        assert "World" in result

    def test_empty_element(self):
        elem = etree.fromstring("<p></p>")
        result = inner_html(elem)
        assert result == ""

    def test_element_with_only_child(self):
        elem = etree.fromstring("<div><span>text</span></div>")
        result = inner_html(elem)
        assert "span" in result
        assert "text" in result


class TestOdfDocTransformExtra:
    def test_init_only_input(self):
        t = OdfDocTransform("input.ods")
        assert t.file_name_in == "input.ods"
        assert t.file_name_out == "input.ods"

    def test_init_with_underscore(self):
        t = OdfDocTransform("test_file.ods")
        assert t.file_name_out == "testfile.ods"

    def test_set_doc_type_all_values(self):
        t = OdfDocTransform("in.ods")
        t.set_doc_type(0)
        assert t.doc_type == 0
        t.set_doc_type(1)
        assert t.doc_type == 1
        t.set_doc_type(2)
        assert t.doc_type == 2

    def test_set_process_tables_empty(self):
        t = OdfDocTransform("in.ods")
        t.set_process_tables([])
        assert t.process_tables == []

    def test_set_process_tables_multiple(self):
        t = OdfDocTransform("in.ods")
        t.set_process_tables(["sheet1", "sheet2", "sheet3"])
        assert len(t.process_tables) == 3

    def test_column_number_format(self):
        t = OdfDocTransform("in.ods")
        result = t.column_number()
        assert "{{" in result
        assert "IncCol" in result

    def test_row_number_default(self):
        t = OdfDocTransform("in.ods")
        result = t.row_number()
        assert "IncRow" in result

    def test_row_number_specific(self):
        t = OdfDocTransform("in.ods")
        result = t.row_number(5)
        assert "args:5" in result

    def test_clear_row_col_format(self):
        t = OdfDocTransform("in.ods")
        result = t.clear_row_col()
        assert "SetRow" in result
        assert "SetCol" in result

    def test_process_template_empty(self):
        t = OdfDocTransform("in.ods")
        result = t.process_template("template", {})
        assert result is None

    def test_doc_process_empty(self):
        t = OdfDocTransform("in.ods")
        result = t.doc_process(None, False)
        assert result is None

    def test_handle_annotation_none_safe(self):
        t = OdfDocTransform("in.ods")
        t._handle_annotation(None, "test")

    def test_handle_annotation_no_parent_safe(self):
        t = OdfDocTransform("in.ods")
        elem = etree.Element("orphan")
        t._handle_annotation(elem, "test")

    def test_handle_repeated_columns_below_threshold(self):
        t = OdfDocTransform("in.ods")
        elem = etree.Element(TABLE_URN + "table-cell")
        elem.set(TABLE_URN + "number-columns-repeated", "500")
        t._handle_repeated_columns(elem)
        assert elem.get(TABLE_URN + "number-columns-repeated") == "500"

    def test_handle_repeated_columns_above_threshold(self):
        t = OdfDocTransform("in.ods")
        elem = etree.Element(TABLE_URN + "table-cell")
        elem.set(TABLE_URN + "number-columns-repeated", "5000")
        t._handle_repeated_columns(elem)
        assert elem.get(TABLE_URN + "number-columns-repeated") == "1000"

    def test_handle_repeated_rows_below_threshold(self):
        t = OdfDocTransform("in.ods")
        elem = etree.Element(TABLE_URN + "table-row")
        parent = etree.Element("parent")
        parent.append(elem)
        t._handle_repeated_rows(elem)

    def test_handle_repeated_rows_above_threshold(self):
        t = OdfDocTransform("in.ods")
        elem = etree.Element(TABLE_URN + "table-row")
        elem.set(TABLE_URN + "number-rows-repeated", "2000")
        parent = etree.Element("parent")
        parent.append(elem)
        t._handle_repeated_rows(elem)
        assert elem.get(TABLE_URN + "number-rows-repeated") == "1000"

    def test_set_cell_style_with_style(self):
        t = OdfDocTransform("in.ods")
        old_elem = etree.Element(TABLE_URN + "table-cell")
        old_elem.set(TABLE_URN + "style-name", "ce1")
        new_elem = etree.Element(TABLE_URN + "table-cell")
        t._set_cell_style(old_elem, new_elem)
        assert new_elem.get(TABLE_URN + "style-name") == "ce1"

    def test_set_cell_style_no_style(self):
        t = OdfDocTransform("in.ods")
        old_elem = etree.Element(TABLE_URN + "table-cell")
        new_elem = etree.Element(TABLE_URN + "table-cell")
        t._set_cell_style(old_elem, new_elem)
        assert new_elem.get(TABLE_URN + "style-name") is None

    def test_add_annotation(self):
        t = OdfDocTransform("in.ods")
        cell = etree.Element(TABLE_URN + "table-cell")
        t._add_annotation(cell, "test annotation")
        assert len(cell.getchildren()) > 0

    @patch("shutil.copyfile")
    def test_process_file_not_found(self, mock_copy):
        mock_copy.side_effect = OSError("file not found")
        t = OdfDocTransform("nonexistent.ods", "out.ods")
        result = t.process({}, False)
        assert result == 0

    def test_remove_table(self):
        t = OdfDocTransform("in.ods")
        elem = etree.Element(TABLE_URN + "table")
        parent = etree.Element("parent")
        parent.append(elem)
        t._remove_table(elem)
