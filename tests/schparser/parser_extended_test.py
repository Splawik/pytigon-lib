"""Tests for :mod:`pytigon_lib.schparser.parser`."""
import io

import pytest

from pytigon_lib.schparser.parser import (
    Elem,
    Parser,
    Script,
    content_tostring,
    tostring,
)


def _make_fake_elem(tag, items=None):
    """Create a fake element with .tag and .items() method."""
    class FakeElem:
        def __init__(self, tag, items):
            self.tag = tag
            self._items = items

        def items(self):
            return self._items() if callable(self._items) else self._items

    return FakeElem(tag, items)


class TestParser:
    def test_init(self):
        p = Parser()
        assert p._tree is None
        assert p._cur_elem is None

    def test_get_starttag_text_no_elem(self):
        p = Parser()
        assert p.get_starttag_text() == ""

    def test_get_starttag_text_with_elem(self):
        p = Parser()
        p._cur_elem = _make_fake_elem("div", [])
        assert p.get_starttag_text() == "<div>"

    def test_get_starttag_text_with_attributes(self):
        p = Parser()
        p._cur_elem = _make_fake_elem("a", [("href", "http://example.com"), ("class", "link")])
        text = p.get_starttag_text()
        assert "href" in text
        assert "example.com" in text

    def test_get_starttag_text_boolean_attr(self):
        p = Parser()
        p._cur_elem = _make_fake_elem("input", [("disabled", "")])
        assert "disabled" in p.get_starttag_text()

    def test_handle_starttag_default(self):
        p = Parser()
        p.handle_starttag("div", {})
        assert True

    def test_handle_data_default(self):
        p = Parser()
        p.handle_data("text")
        assert True

    def test_handle_endtag_default(self):
        p = Parser()
        p.handle_endtag("div")
        assert True

    def test_close_clears_tree(self):
        p = Parser()
        p._tree = {"fake": "tree"}
        p.close()
        assert p._tree is None

    def test_from_html_html_parsing(self):
        p = Parser()
        tree = p.from_html("<html><body><p>Hello</p></body></html>")
        assert tree is not None

    def test_init_with_string(self):
        p = Parser()
        p.init("<html><body>test</body></html>")
        assert p._tree is not None

    def test_init_with_elem(self):
        p = Parser()
        elem = p.from_html("<div>hello</div>")
        wrapped = Elem(elem)
        p.init(wrapped)
        assert p._tree is not None

    def test_init_invalid_html(self):
        p = Parser()
        p.init("")
        assert p._tree is None

    def test_feed_html(self):
        p = Parser()
        p.feed("<div>hello</div>")
        assert True

    def test_feed_empty_tree(self):
        p = Parser()
        p._tree = None
        p.init = lambda *a: None
        p.feed("test")


class TestTostring:
    def test_tostring_div(self):
        tree = Parser.from_html("<div>hello</div>")
        result = tostring(tree)
        assert "div" in result.lower()

    def test_content_tostring(self):
        tree = Parser.from_html("<p>Hello <b>World</b>!</p>")
        result = content_tostring(tree)
        assert "Hello" in result
        assert "World" in result


class TestElem:
    def test_str(self):
        tree = Parser.from_html("<div></div>")
        e = Elem(tree)
        assert "<div>" in str(e)

    def test_str_none_elem(self):
        e = Elem(None)
        assert str(e) == ""

    def test_len(self):
        tree = Parser.from_html("<div>hello</div>")
        e = Elem(tree)
        assert len(e) > 0

    def test_bool_true(self):
        tree = Parser.from_html("<div></div>")
        e = Elem(tree)
        assert bool(e) is True

    def test_bool_false(self):
        e = Elem(None)
        assert bool(e) is False

    def test_super_strip(self):
        e = Elem(None)
        assert e.super_strip("  \t  Hello  \t  ") == "Hello"
        assert e.super_strip("Hello\n\nWorld") == "Hello\n\nWorld"
        assert e.super_strip("") == ""
        assert e.super_strip("  \\n\\n  Hello  \\n  ") == "Hello"

    def test_tostream_div(self):
        tree = Parser.from_html("<div>Hello</div>")
        e = Elem(tree)
        output = e.tostream()
        result = output.getvalue()
        assert "div" in result
        assert "Hello" in result

    def test_tostream_nested(self):
        tree = Parser.from_html("<div><p>Hello</p></div>")
        e = Elem(tree)
        output = e.tostream()
        result = output.getvalue()
        assert "div" in result
        assert "p" in result
        assert "Hello" in result

    def test_tostream_with_output(self):
        tree = Parser.from_html("<div></div>")
        e = Elem(tree)
        buf = io.StringIO()
        output = e.tostream(output=buf)
        assert output is buf

    def test_tostream_none_elem(self):
        e = Elem(None)
        output = e.tostream()
        assert output is not None

    def test_custom_tostring(self):
        tree = Parser.from_html("<div>test</div>")
        e = Elem(tree, tostring_fun=lambda x: "CUSTOM")
        assert str(e) == "CUSTOM"
        assert len(e) == 6


class TestScript:
    def test_script_exists(self):
        from pytigon_lib.schparser.parser import Script

        assert Script is not None

    def test_script_none_elem(self):
        s = Script(None)
        assert str(s) == ""
        assert bool(s) is False


class TestParserCrawl:
    def test_custom_parser_crawls_tree(self):
        class MyParser(Parser):
            def __init__(self):
                super().__init__()
                self.tags = []
                self.data = []
                self.end_tags = []

            def handle_starttag(self, tag, attrib):
                self.tags.append(tag)

            def handle_data(self, txt):
                self.data.append(txt.strip())

            def handle_endtag(self, tag):
                self.end_tags.append(tag)

        p = MyParser()
        p.feed("<div>Hello <b>World</b></div>")
        assert "div" in p.tags
        assert "b" in p.tags
        assert "Hello" in p.data
        assert "World" in p.data
        assert "div" in p.end_tags
        assert "b" in p.end_tags
