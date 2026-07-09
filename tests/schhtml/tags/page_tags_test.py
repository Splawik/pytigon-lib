"""Tests for :mod:`pytigon_lib.schhtml.tags.page_tags`."""
import io
from unittest.mock import MagicMock

from pytigon_lib.schhtml.tags.page_tags import Page, NewPage, HeaderFooter


class TestPageTag:
    def test_page_is_class(self):
        assert isinstance(Page, type)

    def test_page_instantiation(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        page = Page(mock_parent, mock_parser, "page", {})
        assert page.tag == "page"
        assert page.parent is mock_parent
        assert page.parser is mock_parser
        assert page.body is mock_parent

    def test_page_child_tags(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        page = Page(mock_parent, mock_parser, "page", {})
        assert "header" in page.child_tags
        assert "footer" in page.child_tags

    def test_page_close(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        page = Page(mock_parent, mock_parser, "page", {})
        page.close()

    def test_page_finish(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        page = Page(mock_parent, mock_parser, "page", {})
        page.finish()
        page.body.page_changed.assert_called_once()

    def test_page_data_from_child(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        page = Page(mock_parent, mock_parser, "page", {})
        page.data_from_child(None, "some data")
        page.parent.data_from_child.assert_called_once_with(None, "some data")


class TestNewPageTag:
    def test_newpage_is_class(self):
        assert isinstance(NewPage, type)

    def test_newpage_instantiation(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        npage = NewPage(mock_parent, mock_parser, "newpage", {})
        assert npage.tag == "newpage"
        assert npage.body is mock_parent

    def test_newpage_close(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        npage = NewPage(mock_parent, mock_parser, "newpage", {})
        npage.close()

    def test_newpage_finish(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        npage = NewPage(mock_parent, mock_parser, "newpage", {})
        npage.finish()
        npage.body.render_new_page.assert_called_once()


class TestHeaderFooterTag:
    def test_headerfooter_is_class(self):
        assert isinstance(HeaderFooter, type)

    def test_headerfooter_instantiation(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        hf = HeaderFooter(mock_parent, mock_parser, "header", {"height": "50"})
        assert hf.tag == "header"
        assert isinstance(hf.data, io.StringIO)

    def test_headerfooter_handle_data(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        hf = HeaderFooter(mock_parent, mock_parser, "header", {})
        hf.handle_data("Header content")
        assert "Header content" in hf.data.getvalue()

    def test_headerfooter_handle_starttag(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        hf = HeaderFooter(mock_parent, mock_parser, "header", {})
        hf.handle_starttag(mock_parser, "div", {"class": "test"})
        result = hf.data.getvalue()
        assert '<div class="test">' in result

    def test_headerfooter_handle_starttag_none_attr(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        hf = HeaderFooter(mock_parent, mock_parser, "header", {})
        hf.handle_starttag(mock_parser, "hr", {"noshade": None})
        result = hf.data.getvalue()
        assert "<hr noshade>" in result

    def test_headerfooter_handle_endtag_child(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        hf = HeaderFooter(mock_parent, mock_parser, "header", {})
        hf.handle_endtag("span")
        result = hf.data.getvalue()
        assert "</span>" in result

    def test_headerfooter_handle_endtag_self(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        hf = HeaderFooter(mock_parent, mock_parser, "header", {})
        result = hf.handle_endtag("header")
        assert result is hf.parent

    def test_headerfooter_close(self):
        mock_parent = MagicMock()
        mock_parser = MagicMock()
        hf = HeaderFooter(mock_parent, mock_parser, "footer", {})
        hf.close()
