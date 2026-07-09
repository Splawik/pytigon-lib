"""Tests for :mod:`pytigon_lib.schhtml.htmlviewer`."""

from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schhtml.basedc import BaseDc
from pytigon_lib.schhtml.htmlviewer import (
    ALIAS_TAG,
    INIT_CSS_STR_BASE,
    BaseRenderingLib,
    HtmlViewerParser,
    set_rendering_lib,
)


class TestAliasTag:
    def test_em_to_i(self):
        assert ALIAS_TAG.get("em") == "i"

    def test_strong_to_b(self):
        assert ALIAS_TAG.get("strong") == "b"

    def test_is_dict(self):
        assert isinstance(ALIAS_TAG, dict)


class TestBaseRenderingLib:
    def test_accept_returns_false(self):
        assert BaseRenderingLib.accept("") is False

    def test_render_returns_none(self):
        result = BaseRenderingLib.render("")
        assert result is None

    def test_render_with_params(self):
        result = BaseRenderingLib.render("html", stream_type="pdf")
        assert result is None


class TestSetRenderingLib:
    def test_callable(self):
        assert callable(set_rendering_lib)


class TestInitCssStr:
    def test_not_empty(self):
        assert len(INIT_CSS_STR_BASE) > 0

    def test_contains_body(self):
        assert "body" in INIT_CSS_STR_BASE.lower()

    def test_contains_font(self):
        assert "font" in INIT_CSS_STR_BASE.lower()


class TestHtmlViewerParserInit:
    def test_initialization_default(self):
        dc = BaseDc()
        p = HtmlViewerParser(dc=dc)
        assert p.dc is dc
        assert p.parse_only is False
        assert p.use_tag_maps is True
        assert p.calc_only is False
        assert p.lp == 1
        assert p.table_lp == 0
        assert p.tdata_tab == []
        assert p.obj_id_dict == {}
        assert p.obj_action_dict == {}
        assert p.tag_parser is None
        assert p.parent_window is None

    def test_initialization_calc_only(self):
        p = HtmlViewerParser(dc=BaseDc(), calc_only=True)
        assert p.calc_only is True

    def test_initialization_parse_only(self):
        p = HtmlViewerParser(dc=BaseDc(), parse_only=True)
        assert p.calc_only is True

    def test_initialization_with_url(self):
        p = HtmlViewerParser(dc=BaseDc(), url="http://example.com")
        assert p.url == "http://example.com"

    def test_initialization_with_base_url(self):
        p = HtmlViewerParser(dc=BaseDc(), base_url="http://base.com")
        assert p.base_url == "http://base.com"

    def test_initialization_no_dc_creates_base_dc(self):
        p = HtmlViewerParser()
        assert isinstance(p.dc, BaseDc)

    def test_initialization_css_type_indent(self):
        p = HtmlViewerParser(dc=BaseDc(), init_css_str="body { }", css_type=HtmlViewerParser.CSS_TYPE_INDENT)
        assert p.css is not None

    def test_initialization_css_type_standard(self):
        p = HtmlViewerParser(dc=BaseDc(), init_css_str="body { }", css_type=HtmlViewerParser.CSS_TYPE_STANDARD)
        assert p.css is not None

    def test_initialization_no_init_css(self):
        p = HtmlViewerParser(dc=BaseDc())
        assert p.css is not None

    def test_initialization_dc_info(self):
        dc = BaseDc()
        p = HtmlViewerParser(dc=dc)
        assert p.dc_info is not None

    def test_initialization_debug_default(self):
        p = HtmlViewerParser(dc=BaseDc())
        assert p.debug is False


class TestHtmlViewerParserHttp:
    def test_set_http_object(self):
        p = HtmlViewerParser(dc=BaseDc())
        http = MagicMock()
        p.set_http_object(http)
        assert p.http is http

    def test_get_http_object_creates_default(self):
        p = HtmlViewerParser(dc=BaseDc())
        http = p.get_http_object()
        assert http is not None

    def test_get_http_object_returns_stored(self):
        p = HtmlViewerParser(dc=BaseDc())
        http = MagicMock()
        p.set_http_object(http)
        assert p.get_http_object() is http


class TestHtmlViewerParserMaxSizes:
    def test_set_max_rendered_size(self):
        p = HtmlViewerParser(dc=BaseDc())
        p.set_max_rendered_size(100, 200)
        assert p._max_width == 100
        assert p._max_height == 200

    def test_get_max_rendered_size_default(self):
        p = HtmlViewerParser(dc=BaseDc())
        assert p.get_max_rendered_size() == (0, 0)

    def test_get_max_rendered_size_after_set(self):
        p = HtmlViewerParser(dc=BaseDc())
        p.set_max_rendered_size(300, 400)
        assert p.get_max_rendered_size() == (300, 400)

    def test_get_max_sizes_uses_dc_and_max_size(self):
        dc = BaseDc()
        dc._maxwidth = 50
        dc._maxheight = 60
        p = HtmlViewerParser(dc=dc)
        p.set_max_rendered_size(500, 600)
        assert p.get_max_sizes() == (500, 600)


class TestHtmlViewerParserRegister:
    def test_register_tdata(self):
        p = HtmlViewerParser(dc=BaseDc())
        p.register_tdata("data", "tag", {"k": "v"})
        assert len(p.tdata_tab) == 1
        assert p.tdata_tab[0] == ("data", "tag", {"k": "v"})

    def test_reg_id_obj(self):
        dc = MagicMock()
        dc.x = 5
        dc.y = 10
        dc.dx = 100
        dc.dy = 200
        p = HtmlViewerParser(dc=dc)
        obj = MagicMock()
        obj.last_rendered_dc = None
        obj.rendered_rects = []
        p.reg_id_obj("my_id", dc, obj)
        assert "my_id" in p.obj_id_dict
        assert p.obj_id_dict["my_id"] is obj
        assert obj.last_rendered_dc is dc
        assert (5, 10, 100, 200) in obj.rendered_rects

    def test_reg_action_obj_new(self):
        dc = MagicMock()
        dc.x = 0
        dc.y = 0
        dc.dx = 0
        dc.dy = 0
        p = HtmlViewerParser(dc=dc)
        obj = MagicMock()
        obj.last_rendered_dc = None
        obj.rendered_rects = []
        p.reg_action_obj("click", dc, obj)
        assert "click" in p.obj_action_dict
        assert p.obj_action_dict["click"] == [obj]

    def test_reg_action_obj_append(self):
        dc = MagicMock()
        dc.x = 0
        dc.y = 0
        dc.dx = 0
        dc.dy = 0
        p = HtmlViewerParser(dc=dc)
        obj1 = MagicMock()
        obj1.rendered_rects = []
        obj2 = MagicMock()
        obj2.rendered_rects = []
        p.reg_action_obj("click", dc, obj1)
        p.reg_action_obj("click", dc, obj2)
        assert len(p.obj_action_dict["click"]) == 2


class TestHtmlViewerParserParentWindow:
    def test_set_parent_window(self):
        p = HtmlViewerParser(dc=BaseDc())
        win = MagicMock()
        p.set_parent_window(win)
        assert p.parent_window is win

    def test_get_parent_window_default(self):
        p = HtmlViewerParser(dc=BaseDc())
        assert p.get_parent_window() is None

    def test_get_parent_window_after_set(self):
        p = HtmlViewerParser(dc=BaseDc())
        win = MagicMock()
        p.set_parent_window(win)
        assert p.get_parent_window() is win


class TestHtmlViewerParserClose:
    def test_close_calls_end_document(self):
        dc = MagicMock()
        p = HtmlViewerParser(dc=dc)
        p.close()
        dc.end_document.assert_called_once()
        dc.close.assert_called_once()

    def test_close_with_no_dc(self):
        p = HtmlViewerParser(dc=BaseDc())
        p.dc = None
        p.close()
