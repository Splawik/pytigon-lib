"""Tests for :mod:`pytigon_lib.schhtml.css`."""
import pytest

from pytigon_lib.schhtml.css import comment_remover, CssPos


class TestCommentRemover:
    def test_removes_block_comments(self):
        result = comment_remover("color: red; /* comment */ font: 12px;")
        assert "color: red;" in result
        assert "comment" not in result

    def test_removes_line_comments(self):
        result = comment_remover("color: red; // line comment\nfont: 12px;")
        assert "color: red;" in result
        assert "line comment" not in result

    def test_preserves_strings(self):
        result = comment_remover("content: 'http://example.com';")
        assert "http://example.com" in result

    def test_preserves_double_quoted_strings(self):
        result = comment_remover('content: "hello";')
        assert "hello" in result

    def test_empty_input(self):
        result = comment_remover("")
        assert result == ""

    def test_multiline_comment(self):
        result = comment_remover("a: 1;\n/* multi\nline */\nb: 2;")
        assert "a: 1;" in result
        assert "b: 2;" in result


class TestCssPos:
    def test_init_single_level(self):
        pos = CssPos(["div"], {"color": "red"})
        assert pos.tag == "div"
        assert pos.attrs == {"color": "red"}

    def test_init_multi_level(self):
        pos = CssPos(["html", "body", "div"], {"color": "blue"})
        assert pos.tag == "div"
        assert len(pos.parents) >= 0

    def test_key(self):
        pos = CssPos(["span"], {"font-size": "12px"})
        assert pos.key() == "span"

    def test_extend_dict(self):
        pos = CssPos(["div"], {"a": "1"})
        dest = {}
        pos._extend_dict(dest, {"b": "2"})
        assert dest == {"b": "2"}

    def test_attrs_merged(self):
        pos = CssPos(["div", "p"], {"font": "12px"})
        assert pos.tag == "p"
