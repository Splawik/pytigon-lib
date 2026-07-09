"""Tests for :mod:`pytigon_lib.schhtml.basehtmltags`."""
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from pytigon_lib.schhtml.basehtmltags import (
    BLOCK_TAGS,
    HTML_TAGS,
    TagPreprocesor,
    BaseHtmlElemParser,
    BaseHtmlAtomParser,
    AnyTag,
    rgb_to_hex,
    register_tag_map,
    register_tag_preprocess_map,
    tag_class_map,
)


class TestRgbToHex:
    def test_rgb_to_hex_red(self):
        assert rgb_to_hex("rgb(255, 0, 0)") == "#ff0000"

    def test_rgb_to_hex_white(self):
        assert rgb_to_hex("rgb(255, 255, 255)") == "#ffffff"

    def test_rgb_to_hex_black(self):
        assert rgb_to_hex("rgb(0, 0, 0)") == "#000000"

    def test_rgb_to_hex_single_digit_components(self):
        assert rgb_to_hex("rgb(0, 1, 0)") == "#000100"

    def test_rgb_to_hex_mixed_values(self):
        assert rgb_to_hex("rgb(0, 128, 255)") == "#0080ff"

    def test_invalid_rgb_returns_default(self):
        assert rgb_to_hex("#ff0000") == "#000"

    def test_empty_string(self):
        assert rgb_to_hex("") == "#000"

    def test_malformed_rgb(self):
        assert rgb_to_hex("rgb(abc)") == "#000"


class TestTagConstants:
    def test_html_tags_is_list(self):
        assert isinstance(HTML_TAGS, list)

    def test_html_tags_not_empty(self):
        assert len(HTML_TAGS) > 0

    def test_block_tags_is_list(self):
        assert isinstance(BLOCK_TAGS, list)

    def test_block_tags_not_empty(self):
        assert len(BLOCK_TAGS) > 0

    def test_html_tags_contains_expected(self):
        assert "html" in HTML_TAGS
        assert "head" in HTML_TAGS


class TestTagRegistry:
    def test_register_stores_in_map(self):
        old = tag_class_map.get("_test_reg")
        try:
            register_tag_map("_test_reg", object)
            assert tag_class_map["_test_reg"] is object
        finally:
            if old is not None:
                tag_class_map["_test_reg"] = old
            else:
                tag_class_map.pop("_test_reg", None)

    def test_register_overwrites_existing(self):
        class A:
            pass

        class B:
            pass

        tag_map_key = "_test_reg_overwrite"
        old = tag_class_map.get(tag_map_key)
        try:
            register_tag_map(tag_map_key, A)
            register_tag_map(tag_map_key, B)
            assert tag_class_map[tag_map_key] is B
        finally:
            if old is not None:
                tag_class_map[tag_map_key] = old
            else:
                tag_class_map.pop(tag_map_key, None)


class TestTagPreprocessor:
    def test_register_and_get_handler_exact_match(self):
        tp = TagPreprocesor()
        handler = lambda parser, tag, attrs: None
        tp.register("div", handler)
        assert tp.get_handler("div") is handler

    def test_get_handler_nonexistent_returns_none(self):
        tp = TagPreprocesor()
        assert tp.get_handler("nonexistent_tag_xyz") is None

    def test_register_with_not_tag_param(self):
        tp = TagPreprocesor()
        handler = lambda parser, tag, attrs: None
        tp.register("div", handler, not_tag="span")
        assert tp.get_handler("div") is handler

    def test_wildcard_match(self):
        tp = TagPreprocesor()
        handler = lambda parser, tag, attrs: None
        tp.register("h*", handler)
        assert tp.get_handler("h1") is handler
        assert tp.get_handler("h2") is handler
        assert tp.get_handler("div") is None

    def test_wildcard_with_not_tag_excludes_match(self):
        tp = TagPreprocesor()
        handler = lambda parser, tag, attrs: None
        tp.register("h*", handler, not_tag="head*")
        assert tp.get_handler("h1") is handler
        assert tp.get_handler("head") is None
        assert tp.get_handler("header") is None

    def test_tag_case_insensitive(self):
        tp = TagPreprocesor()
        handler = lambda parser, tag, attrs: None
        tp.register("DIV", handler)
        assert tp.get_handler("div") is handler

    def test_empty_preprocessor_returns_none(self):
        tp = TagPreprocesor()
        assert tp.get_handler("div") is None


class TestPreprocessMap:
    def test_global_map_exists(self):
        from pytigon_lib.schhtml.basehtmltags import TAG_PREPROCESS_MAP

        assert TAG_PREPROCESS_MAP is not None
        assert isinstance(TAG_PREPROCESS_MAP, TagPreprocesor)

    def test_register_uses_global_map(self):
        from pytigon_lib.schhtml.basehtmltags import TAG_PREPROCESS_MAP

        handler = lambda parser, tag, attrs: None
        register_tag_preprocess_map("_test_global_pp", handler)
        assert TAG_PREPROCESS_MAP.get_handler("_test_global_pp") is handler


class TestBaseHtmlElemParserInit:
    def _make_parser(self):
        parser = MagicMock()
        parser.css.get_dict.return_value = {}
        return parser

    def test_init_stores_tag_and_attrs(self):
        parser = self._make_parser()
        parent = MagicMock()
        tag = BaseHtmlElemParser(parent, parser, "div", {"class": "foo"})
        assert tag.tag == "div"
        assert tag.attrs == {"class": "foo"}

    def test_init_default_values(self):
        parser = self._make_parser()
        parent = MagicMock()
        tag = BaseHtmlElemParser(parent, parser, "span", {})
        assert tag.width == -1
        assert tag.height == -1
        assert tag.dy == 0
        assert tag.child_tags == []
        assert tag.data == []

    def test_init_stores_parent(self):
        parser = self._make_parser()
        parent = MagicMock()
        tag = BaseHtmlElemParser(parent, parser, "span", {})
        assert tag.parent is parent

    def test_init_stores_parser(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "span", {})
        assert tag.parser is parser

    def test_init_close_tag_equals_tag(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        assert tag.close_tag == "div"

    def test_init_rendered_children_empty(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        assert tag.rendered_children == []

    def test_init_reg_flag_true(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        assert tag.reg_flag is True

    def test_init_sys_id_default(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        assert tag.sys_id == -1

    def test_init_hover_defaults(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        assert tag.hover is False
        assert tag.hover_css_attrs == {}

    def test_init_form_obj_none(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        assert tag.form_obj is None

    def test_init_gparent_is_self(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        assert tag.gparent is tag

    def test_init_max_min_width_height(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        assert tag.max_width == 1000000000
        assert tag.min_width == -1000000000
        assert tag.max_height == 1000000000
        assert tag.min_height == -1000000000


class TestBaseHtmlElemParserMethods:
    def _make_parser(self):
        parser = MagicMock()
        parser.css.get_dict.return_value = {}
        return parser

    def test_get_parent_returns_parent(self):
        parser = self._make_parser()
        parent = MagicMock()
        tag = BaseHtmlElemParser(parent, parser, "div", {})
        assert tag.get_parent() is parent

    def test_get_tag_returns_lowercase(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "DIV", {})
        assert tag.get_tag() == "div"

    def test_get_id_returns_lowercase(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {"id": "MyID"})
        assert tag.get_id() == "myid"

    def test_get_id_none_when_missing(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        assert tag.get_id() is None

    def test_get_cls_returns_lowercase(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {"class": "MyClass"})
        assert tag.get_cls() == "myclass"

    def test_get_cls_none_when_missing(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        assert tag.get_cls() is None

    def test_str_representation(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {"class": "foo"})
        assert str(tag) == "div:{'class': 'foo'}"

    def test_str_representation_empty_attrs(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "span", {})
        assert str(tag) == "span:{}"

    def test_get_atrr_returns_own_attr(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {"color": "red"})
        assert tag.get_atrr("color") == "red"

    def test_get_atrr_returns_parent_attr_when_missing(self):
        parser = self._make_parser()
        parent = BaseHtmlElemParser(MagicMock(), parser, "div", {"font-size": "12px"})
        child = BaseHtmlElemParser(parent, parser, "span", {})
        assert child.get_atrr("font-size") == "12px"

    def test_get_atrr_none_not_found(self):
        parser = self._make_parser()
        parent = MagicMock()
        parent.get_parent.return_value = None
        tag = BaseHtmlElemParser(parent, parser, "div", {})
        assert tag.get_atrr("missing") is None

    def test_get_atrr_lowercases_value(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {"align": "CENTER"})
        assert tag.get_atrr("align") == "center"

    def test_set_hover_enable(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        tag.set_hover(True)
        assert tag.hover is True
        tag.set_hover(False)
        assert tag.hover is False

    def test_can_hover_false_by_default(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        assert tag.can_hover() is False

    def test_can_hover_true_with_css_attrs(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        tag.hover_css_attrs = {"color": "red"}
        assert tag.can_hover() is True

    def test_set_width_updates_width(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        tag.set_width(100)
        assert tag.width == 100

    def test_set_height_updates_height(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        tag.set_height(200)
        assert tag.height == 200

    def test_height_property_negative_one_default(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        assert tag.height == -1

    def test_set_dc_info_stores_reference(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        dc_info = MagicMock()
        tag.set_dc_info(dc_info)
        assert tag.dc_info is dc_info

    def test_reg_end_sets_reg_flag_false(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        assert tag.reg_flag is True
        tag.reg_end()
        assert tag.reg_flag is False

    def test_handle_data_appends_to_data_list(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        tag.handle_data("hello")
        tag.handle_data(" world")
        assert tag.data == ["hello", " world"]

    def test_finish_does_not_raise(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        tag.finish()

    def test_calc_width_returns_defaults(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        assert tag.calc_width() == (-1, -1, -1)

    def test_calc_height_returns_10(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        assert tag.calc_height() == 10

    def test_handle_endtag_matching_returns_parent(self):
        parser = self._make_parser()
        parent = MagicMock()
        child = BaseHtmlElemParser(parent, parser, "div", {})
        result = child.handle_endtag("div")
        assert result is parent

    def test_handle_endtag_non_matching_returns_self(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        result = tag.handle_endtag("span")
        assert result is tag

    def test__get_pseudo_margins_returns_zeros(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        assert tag._get_pseudo_margins() == [0, 0, 0, 0]

    def test__get_parent_pseudo_margins_no_parent(self):
        parser = self._make_parser()
        parent = MagicMock()
        parent._get_parent_pseudo_margins.return_value = [0, 0, 0, 0]
        tag = BaseHtmlElemParser(parent, parser, "div", {})
        assert tag._get_parent_pseudo_margins() == [0, 0, 0, 0]

    def test__get_parent_pseudo_margins_accumulates(self):
        parser = self._make_parser()
        parent = MagicMock()
        parent._get_parent_pseudo_margins.return_value = [1, 2, 3, 4]
        tag = BaseHtmlElemParser(parent, parser, "div", {})
        assert tag._get_parent_pseudo_margins() == [1, 2, 3, 4]

    def test_get_parent_width_no_parent_returns_negative_one(self):
        parser = self._make_parser()
        parent = MagicMock()
        parent.parent = None
        parent.width = -1
        tag = BaseHtmlElemParser(parent, parser, "div", {})
        assert tag.get_parent_width() == -1

    def test_get_parent_height_no_parent_returns_negative_one(self):
        parser = self._make_parser()
        parent = MagicMock()
        parent.parent = None
        parent.height = -1
        tag = BaseHtmlElemParser(parent, parser, "div", {})
        assert tag.get_parent_height() == -1

    def test_take_into_account_minmax_no_scaling(self):
        parser = self._make_parser()
        tag = BaseHtmlElemParser(MagicMock(), parser, "div", {})
        tag.max_width = 800
        tag.min_width = 100
        tag.max_height = 600
        tag.min_height = 50
        assert tag.take_into_account_minmax(50, 20) == (100, 50)
        assert tag.take_into_account_minmax(1000, 700) == (800, 600)
        assert tag.take_into_account_minmax(400, 300) == (400, 300)


class TestBaseHtmlAtomParser:
    def _make_parser(self):
        parser = MagicMock()
        parser.css.get_dict.return_value = {}
        return parser

    def test_init_creates_atom_parser(self):
        parser = self._make_parser()
        tag = BaseHtmlAtomParser(MagicMock(), parser, "p", {})
        assert tag.atom_list is None
        assert tag.atom_dy == 0
        assert tag.style == -1
        assert tag.no_wrap is False

    def test_init_pre_false_by_default(self):
        parser = self._make_parser()
        tag = BaseHtmlAtomParser(MagicMock(), parser, "p", {})
        assert tag.pre is False

    def test_init_pre_true_with_white_space_pre(self):
        parser = self._make_parser()
        tag = BaseHtmlAtomParser(MagicMock(), parser, "p", {"white-space": "pre"})
        assert tag.pre is True

    def test_init_line_spacing_sets_atom_dy(self):
        parser = self._make_parser()
        tag = BaseHtmlAtomParser(MagicMock(), parser, "p", {"line-spacing": "1.5"})
        assert tag.atom_dy == 1.5

    def test_set_atom_dy_updates_property(self):
        parser = self._make_parser()
        tag = BaseHtmlAtomParser(MagicMock(), parser, "p", {})
        tag.set_atom_dy(2.0)
        assert tag.atom_dy == 2.0

    def test_set_atom_dy_updates_atom_list_when_exists(self):
        parser = self._make_parser()
        tag = BaseHtmlAtomParser(MagicMock(), parser, "p", {})
        tag.atom_list = MagicMock()
        tag.set_atom_dy(3.0)
        assert tag.atom_dy == 3.0
        tag.atom_list.set_line_dy.assert_called_once_with(3.0)

    def test_make_atom_list_creates_new(self):
        parser = self._make_parser()
        tag = BaseHtmlAtomParser(MagicMock(), parser, "p", {})
        tag.dc_info = MagicMock()
        tag.make_atom_list()
        assert tag.atom_list is not None

    def test_make_atom_list_sets_justify(self):
        parser = self._make_parser()
        tag = BaseHtmlAtomParser(MagicMock(), parser, "p", {"text-align": "justify"})
        tag.dc_info = MagicMock()
        tag.make_atom_list()
        assert tag.atom_list is not None

    def test_make_atom_list_idempotent(self):
        parser = self._make_parser()
        tag = BaseHtmlAtomParser(MagicMock(), parser, "p", {})
        tag.dc_info = MagicMock()
        tag.make_atom_list()
        first = tag.atom_list
        tag.make_atom_list()
        assert tag.atom_list is first

    def test_handle_data_strips_and_appends(self):
        parser = self._make_parser()
        parser.css.get_dict.return_value = {}
        dc_info = MagicMock()
        dc_info.get_style_id.return_value = 42
        parent = BaseHtmlElemParser(None, parser, "body", {
            "color": "#000",
            "font-family": "sans-serif",
            "font-size": "100%",
            "font-style": "normal",
            "font-weight": "normal",
            "text-decoration": "none",
        })
        tag = BaseHtmlAtomParser(parent, parser, "span", {})
        tag.dc_info = dc_info
        tag.make_atom_list()
        tag.handle_data("  Hello  ")
        assert len(tag.atom_list.atom_list) > 0

    def test_handle_data_pre_mode_does_not_strip(self):
        parser = self._make_parser()
        parser.css.get_dict.return_value = {}
        dc_info = MagicMock()
        dc_info.get_style_id.return_value = 42
        parent = BaseHtmlElemParser(None, parser, "body", {
            "color": "#000",
            "font-family": "sans-serif",
            "font-size": "100%",
            "font-style": "normal",
            "font-weight": "normal",
            "text-decoration": "none",
        })
        tag = BaseHtmlAtomParser(parent, parser, "pre", {"white-space": "pre"})
        tag.dc_info = dc_info
        tag.make_atom_list()
        tag.handle_data("   spaced   ")
        assert len(tag.atom_list.atom_list) > 0


class TestAnyTag:
    def test_init_creates_any_tag(self):
        parser = MagicMock()
        parser.css.get_dict.return_value = {}
        tag = AnyTag(MagicMock(), parser, "any", {})
        assert tag.tag == "any"
        assert "a" in tag.child_tags
        assert "p" in tag.child_tags
        assert "pre" in tag.child_tags
        assert "div" in tag.child_tags

    def test_close_does_not_call_parent(self):
        parser = MagicMock()
        parser.css.get_dict.return_value = {}
        parent = MagicMock()
        tag = AnyTag(parent, parser, "any", {})
        tag.close()
        parent.child_ready_to_render.assert_not_called()


class TestHtmlTag:
    def test_is_subclass_of_base(self):
        from pytigon_lib.schhtml.basehtmltags import BaseHtmlElemParser
        from pytigon_lib.schhtml.html_tags import HtmlTag

        assert issubclass(HtmlTag, BaseHtmlElemParser)

    def test_header_tag_is_class(self):
        from pytigon_lib.schhtml.html_tags import HeaderTag

        assert isinstance(HeaderTag, type)

    def test_comment_tag_is_class(self):
        from pytigon_lib.schhtml.html_tags import CommentTag

        assert isinstance(CommentTag, type)
