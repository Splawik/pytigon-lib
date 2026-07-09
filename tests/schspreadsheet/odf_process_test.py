"""Tests for :mod:`pytigon_lib.schspreadsheet.odf_process`."""
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schspreadsheet.odf_process import (
    OdfDocTransform,
    attr_get,
    inner_html,
    transform_str,
)


class TestOdfProcess:
    def test_module_import(self):
        from pytigon_lib.schspreadsheet import odf_process

        assert odf_process.OFFICE_URN
        assert odf_process.TABLE_URN
        assert odf_process.TEXT_URN

    def test_attr_get(self):
        attrs = {"{urn}name": "test", "{urn}style": "bold"}
        assert attr_get(attrs, "name") == "test"
        assert attr_get(attrs, "style") == "bold"
        assert attr_get(attrs, "missing") is None
        assert attr_get({}, "any") is None

    def test_transform_str(self):
        assert transform_str("x***y") == 'x"y'
        assert transform_str("x**y") == "x'y"
        assert transform_str("normal") == "normal"

    def test_odf_doctransform_init(self):
        t = OdfDocTransform("input.ods", "output.ods")
        assert t.file_name_in == "input.ods"
        assert t.file_name_out == "output.ods"
        assert t.doc_type == 1
        assert t.buf is None
        assert t.auto_cells is False

    def test_odf_doctransform_init_auto_output(self):
        t = OdfDocTransform("test_file.ods")
        assert t.file_name_out == "testfile.ods"

    def test_set_doc_type(self):
        t = OdfDocTransform("in.ods")
        t.set_doc_type(2)
        assert t.doc_type == 2

    def test_set_process_tables(self):
        t = OdfDocTransform("in.ods")
        t.set_process_tables(["table1", "table2"])
        assert t.process_tables == ["table1", "table2"]

    def test_column_number(self):
        t = OdfDocTransform("in.ods")
        assert "IncCol" in t.column_number()

    def test_row_number(self):
        t = OdfDocTransform("in.ods")
        result = t.row_number(3)
        assert "IncRow" in result
        assert "SetCol" in result

    def test_clear_row_col(self):
        t = OdfDocTransform("in.ods")
        result = t.clear_row_col()
        assert "SetRow" in result
        assert "SetCol" in result

    def test_inner_html(self):
        from lxml import etree

        elem = etree.fromstring("<p>Hello <b>World</b></p>")
        result = inner_html(elem)
        assert "Hello" in result
        assert "World" in result

    def test_handle_annotation_none(self):
        t = OdfDocTransform("in.ods")
        t._handle_annotation(None, "test")

    def test_handle_annotation_no_parent(self):
        from lxml import etree

        t = OdfDocTransform("in.ods")
        elem = etree.Element("orphan")
        t._handle_annotation(elem, "test")

    def test_process_annotations_no_annotations(self):
        from lxml import etree

        t = OdfDocTransform("in.ods")
        root = etree.fromstring("<root><p>No annotations</p></root>")
        t._process_annotations(root, False)

    @patch("shutil.copyfile")
    def test_process_file_not_found(self, mock_copyfile):
        mock_copyfile.side_effect = OSError("file not found")
        t = OdfDocTransform("nonexistent.ods", "out.ods")
        result = t.process({}, False)
        assert result == 0
