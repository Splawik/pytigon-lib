"""Tests for :mod:`pytigon_lib.schhtml.tags.css_tags`."""
from unittest.mock import MagicMock

from pytigon_lib.schhtml.tags.css_tags import Css, CssLink


class TestCssTag:
    def test_css_is_class(self):
        assert isinstance(Css, type)

    def test_css_instantiation(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        css = Css(mock_parent, mock_parser, "style", {"type": "text/css"})
        assert css.tag == "style"
        assert css.attrs == {"type": "text/css"}
        assert css.parent is mock_parent
        assert css.parser is mock_parser

    def test_css_empty_data(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        css = Css(mock_parent, mock_parser, "style", {})
        css.data = []
        css.close()

    def test_css_with_data_calls_parse_str(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        css = Css(mock_parent, mock_parser, "style", {})
        css.data = ["body { color: red; }"]
        css.close()
        mock_parser.css.parse_str.assert_called_once_with("body { color: red; }")

    def test_css_height_property(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        css = Css(mock_parent, mock_parser, "style", {})
        assert css.height == -1
        css.height = 100
        assert css.height == 100

    def test_css_width_attribute(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        css = Css(mock_parent, mock_parser, "style", {"width": "500px"})
        assert css.width >= 0

    def test_css_data_collection(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        css = Css(mock_parent, mock_parser, "style", {})
        css.handle_data(".test { margin: 0; }")
        assert ".test { margin: 0; }" in css.data


class TestCssLinkTag:
    def test_csslink_is_class(self):
        assert isinstance(CssLink, type)

    def test_csslink_instantiation(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        link = CssLink(mock_parent, mock_parser, "link", {"href": "style.css", "rel": "stylesheet"})
        assert link.tag == "link"
        assert link.attrs["href"] == "style.css"

    def test_csslink_close_no_href(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        link = CssLink(mock_parent, mock_parser, "link", {})
        link.close()

    def test_csslink_close_ico_skip(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        link = CssLink(mock_parent, mock_parser, "link", {"href": "favicon.ico"})
        link.close()

    def test_csslink_close_with_href(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.ret_code = 200
        mock_response.str.return_value = "h1 { font-size: 20px; }"
        mock_http.get.return_value = mock_response
        mock_parser.get_http_object.return_value = mock_http

        link = CssLink(mock_parent, mock_parser, "link", {"href": "style.css"})
        link.close()
        mock_http.get.assert_called_once_with(link, "style.css")
        mock_parser.css.parse_str.assert_called_once_with("h1 { font-size: 20px; }")

    def test_csslink_close_http_error(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        mock_http = MagicMock()
        mock_response = MagicMock()
        mock_response.ret_code = 404
        mock_http.get.return_value = mock_response
        mock_parser.get_http_object.return_value = mock_http

        link = CssLink(mock_parent, mock_parser, "link", {"href": "missing.css"})
        link.close()
        mock_http.get.assert_called_once_with(link, "missing.css")
        mock_parser.css.parse_str.assert_not_called()
