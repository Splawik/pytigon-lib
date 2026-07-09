"""Tests for :mod:`pytigon_lib.schhtml.tags.block_tags`."""

from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schhtml.basehtmltags import tag_class_map, register_tag_map
from pytigon_lib.schhtml.tags.block_tags import BodyTag, FormTag


class TestBodyTag:
    def test_bodytag_is_class(self):
        assert isinstance(BodyTag, type)

    def test_bodytag_instantiation(self):
        mock_parent = MagicMock()
        mock_parent.dc.get_size.return_value = (800, 600)
        mock_subdc = MagicMock()
        mock_subdc.get_size.return_value = (800, 600)
        mock_parent.dc.subdc.return_value = mock_subdc
        mock_parser = MagicMock()
        body = BodyTag(mock_parent, mock_parser, "body", {})
        assert body.tag == "body"
        assert body.page == 1
        assert body.y == 0

    def test_bodytag_has_extra_space(self):
        mock_parent = MagicMock()
        mock_parent.dc.get_size.return_value = (800, 600)
        mock_subdc = MagicMock()
        mock_subdc.get_size.return_value = (800, 600)
        mock_parent.dc.subdc.return_value = mock_subdc
        mock_parser = MagicMock()
        body = BodyTag(mock_parent, mock_parser, "body", {})
        assert len(body.extra_space) == 4
        assert len(body.margins) == 4

    def test_bodytag_pseudo_margins(self):
        mock_parent = MagicMock()
        mock_parent.dc.get_size.return_value = (800, 600)
        mock_subdc = MagicMock()
        mock_subdc.get_size.return_value = (800, 600)
        mock_parent.dc.subdc.return_value = mock_subdc
        mock_parser = MagicMock()
        body = BodyTag(mock_parent, mock_parser, "body", {})
        margins = body._get_pseudo_margins()
        assert isinstance(margins, list)
        assert len(margins) == 4

    def test_bodytag_data_from_child_header(self):
        mock_parent = MagicMock()
        mock_parent.dc.get_size.return_value = (800, 600)
        mock_subdc = MagicMock()
        mock_subdc.get_size.return_value = (800, 600)
        mock_parent.dc.subdc.return_value = mock_subdc
        mock_parser = MagicMock()
        body = BodyTag(mock_parent, mock_parser, "body", {})
        child = MagicMock()
        child.tag = "header"
        child.data = MagicMock()
        child.data.getvalue.return_value = "<div>Header</div>"
        child.attrs = {"height": "80"}
        body.data_from_child(child, child.data)
        assert body.header == "<div>Header</div>"
        assert body.header_height == 80

    def test_bodytag_data_from_child_footer(self):
        mock_parent = MagicMock()
        mock_parent.dc.get_size.return_value = (800, 600)
        mock_subdc = MagicMock()
        mock_subdc.get_size.return_value = (800, 600)
        mock_parent.dc.subdc.return_value = mock_subdc
        mock_parser = MagicMock()
        body = BodyTag(mock_parent, mock_parser, "body", {})
        child = MagicMock()
        child.tag = "footer"
        child.data = MagicMock()
        child.data.getvalue.return_value = "<div>Footer</div>"
        child.attrs = {"height": "0"}
        body.data_from_child(child, child.data)
        assert body.footer == "<div>Footer</div>"
        assert body.footer_height == 60

    def test_bodytag_page_changed_no_base_state(self):
        mock_parent = MagicMock()
        mock_parent.dc.get_size.return_value = (800, 600)
        mock_dc = MagicMock()
        mock_dc.get_size.return_value = (800, 600)
        mock_dc.paging = True
        mock_parent.dc = mock_dc
        mock_subdc = MagicMock()
        mock_subdc.get_size.return_value = (800, 600)
        mock_parent.dc.subdc.return_value = mock_subdc
        mock_parser = MagicMock()
        body = BodyTag(mock_parent, mock_parser, "body", {})
        body.base_state = None
        body.new_page = 1
        body.page_changed()

    def test_bodytag_print_header_none(self):
        mock_parent = MagicMock()
        mock_parent.dc.get_size.return_value = (800, 600)
        mock_subdc = MagicMock()
        mock_subdc.get_size.return_value = (800, 600)
        mock_parent.dc.subdc.return_value = mock_subdc
        mock_parser = MagicMock()
        body = BodyTag(mock_parent, mock_parser, "body", {})
        body.header = None
        body.print_header()
        assert body.y == 0

    def test_bodytag_close_parse_only(self):
        mock_parent = MagicMock()
        mock_parent.dc.get_size.return_value = (800, 600)
        mock_subdc = MagicMock()
        mock_subdc.get_size.return_value = (800, 600)
        mock_parent.dc.subdc.return_value = mock_subdc
        mock_parser = MagicMock()
        mock_parser.parse_only = True
        body = BodyTag(mock_parent, mock_parser, "body", {})
        body.close()

    def test_bodytag_set_dc_info(self):
        mock_parent = MagicMock()
        mock_parent.dc.get_size.return_value = (800, 600)
        mock_subdc = MagicMock()
        mock_subdc.get_size.return_value = (800, 600)
        mock_parent.dc.subdc.return_value = mock_subdc
        mock_parser = MagicMock()
        body = BodyTag(mock_parent, mock_parser, "body", {})
        mock_dc_info = MagicMock()
        with patch.object(body, "get_style_id", return_value=1):
            body.set_dc_info(mock_dc_info)
            assert body.dc_info is mock_dc_info

    def test_bodytag_render_helpers_count(self):
        mock_parent = MagicMock()
        mock_parent.dc.get_size.return_value = (800, 600)
        mock_subdc = MagicMock()
        mock_subdc.get_size.return_value = (800, 600)
        mock_parent.dc.subdc.return_value = mock_subdc
        mock_parser = MagicMock()
        body = BodyTag(mock_parent, mock_parser, "body", {})
        assert len(body.render_helpers) == 4


class TestFormTag:
    def test_formtag_is_class(self):
        assert isinstance(FormTag, type)

    def test_formtag_instantiation(self):
        mock_parent = MagicMock()
        mock_parent.child_tags = []
        mock_parser = MagicMock()
        form = FormTag(mock_parent, mock_parser, "form", {"method": "POST", "action": "/submit"})
        assert form.tag == "form"
        assert form.field_names == {}
        assert form.fields is None

    def test_formtag_handle_data(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        mock_parent.child_tags = []
        form = FormTag(mock_parent, mock_parser, "form", {})
        form.handle_data("some data")

    def test_formtag_reg_field(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        mock_parent.child_tags = []
        form = FormTag(mock_parent, mock_parser, "form", {})
        result = form.reg_field("username")
        assert result == "username"
        assert form.fields == "username"

    def test_formtag_reg_field_duplicate(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        mock_parent.child_tags = []
        form = FormTag(mock_parent, mock_parser, "form", {})
        form.reg_field("email")
        result = form.reg_field("email")
        assert result == "email__2"
        assert "email,email__2" in form.fields

    def test_formtag_reg_field_underscore(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        mock_parent.child_tags = []
        form = FormTag(mock_parent, mock_parser, "form", {})
        result = form.reg_field("_hidden")
        assert result == "_hidden"
        assert form.fields is None

    def test_formtag_get_fields_empty(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        mock_parent.child_tags = []
        form = FormTag(mock_parent, mock_parser, "form", {})
        assert form.get_fields() is None

    def test_formtag_get_fields(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        mock_parent.child_tags = []
        form = FormTag(mock_parent, mock_parser, "form", {"method": "POST"})
        form.fields = "name,email"
        result = form.get_fields()
        assert result == "POST:name,email"

    def test_formtag_gethref(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        mock_parent.child_tags = []
        form = FormTag(mock_parent, mock_parser, "form", {"action": "/api/submit"})
        assert form.gethref() == "/api/submit"

    def test_formtag_set_get_upload(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        mock_parent.child_tags = []
        form = FormTag(mock_parent, mock_parser, "form", {})
        form.set_upload("file_data")
        assert form.get_upload() == "file_data"

    def test_formtag_parent_form_obj(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        mock_parent.child_tags = []
        form = FormTag(mock_parent, mock_parser, "form", {})
        assert mock_parent.form_obj is form

    def test_formtag_close_cleans_parent(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        mock_parent.child_tags = []
        form = FormTag(mock_parent, mock_parser, "form", {})
        form.close()
        assert mock_parent.form_obj is None

    def test_formtag_handle_starttag(self):
        mock_div_cls = MagicMock(return_value=MagicMock())
        register_tag_map("div", mock_div_cls)

        mock_parent = MagicMock()
        mock_parent.child_tags = ["div"]
        mock_parser = MagicMock()
        form = FormTag(mock_parent, mock_parser, "form", {})
        result = form.handle_starttag(mock_parser, "div", {})
        assert result is not None
        mock_div_cls.assert_called_once_with(form, mock_parser, "div", {})
