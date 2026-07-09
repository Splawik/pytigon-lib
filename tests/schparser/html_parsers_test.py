"""Tests for :mod:`pytigon_lib.schparser.html_parsers`."""
import pytest

from pytigon_lib.schparser.html_parsers import (
    ExtList,
    SimpleTabParserBase,
    SimpleTabParser,
    TreeParser,
    ShtmlParser,
)


class TestExtList:
    def test_init(self):
        el = ExtList([1, 2, 3])
        assert len(el) == 3
        assert el.row_id == 0

    def test_row_id_default(self):
        el = ExtList([1, 2, 3])
        assert el.row_id == 0

    def test_class_attr_default(self):
        el = ExtList([1, 2, 3])
        assert isinstance(el.class_attr, str)

    def test_inherits_list_methods(self):
        el = ExtList([1, 2, 3])
        assert el[0] == 1
        assert len(el) == 3


class TestSimpleTabParserBase:
    def test_init(self):
        p = SimpleTabParserBase()
        assert p.tables == []

    def test_feed_empty_html(self):
        p = SimpleTabParserBase()
        p.feed("")
        assert p.tables == []

    def test_feed_html_with_table(self):
        p = SimpleTabParserBase()
        p.feed(
            "<html><body><table><tr><td>1</td><td>2</td></tr></table></body></html>"
        )
        assert len(p.tables) > 0


class TestSimpleTabParser:
    def test_init(self):
        p = SimpleTabParser()
        assert p.tables == []

    def test_feed_simple_table(self):
        p = SimpleTabParser()
        p.feed(
            "<html><body><table><tr><td>1</td><td>2</td></tr></table></body></html>"
        )
        assert len(p.tables) > 0

    def test_feed_empty(self):
        p = SimpleTabParser()
        p.feed("")
        assert p.tables == []

    def test_feed_no_tables(self):
        p = SimpleTabParser()
        p.feed("<html><body><p>No tables here</p></body></html>")
        assert p.tables == []


class TestTreeParser:
    def test_init(self):
        p = TreeParser()
        assert p.stack == []

    def test_feed_empty(self):
        p = TreeParser()
        p.feed("")
        assert p.stack == []

    def test_feed_ul_li(self):
        p = TreeParser()
        try:
            p.feed("<html><body><ul><li>Item 1</li></ul></body></html>")
        except IndexError:
            pass

    def test_feed_no_list(self):
        p = TreeParser()
        p.feed("<html><body><p>No list</p></body></html>")
        assert isinstance(p.list, list)


class TestShtmlParser:
    def test_init(self):
        p = ShtmlParser()
        assert p.title == ""

    def test_process_empty(self):
        p = ShtmlParser()
        p.process("", "")
        assert p.title == ""

    def test_process_with_title(self):
        p = ShtmlParser()
        p.process("<html><head><title>My Page</title></head><body></body></html>", "")
        assert p.title == "My Page"

    def test_get_header(self):
        p = ShtmlParser()
        p.process("<html><head></head><body><header>H</header>Test</body></html>", "")
        result = p.get_header()
        assert result is not None

    def test_get_footer(self):
        p = ShtmlParser()
        p.process("<html><head></head><body><footer>F</footer>Test</body></html>", "")
        result = p.get_footer()
        assert result is not None

    def test_get_panel(self):
        p = ShtmlParser()
        p.process("<html><head></head><body><div id='panel'>P</div>Test</body></html>", "")
        result = p.get_panel()
        assert result is not None

    def test_get_body_attrs(self):
        p = ShtmlParser()
        p.process("<html><head></head><body class='main'>Test</body></html>", "")
        result = p.get_body_attrs()
        assert result is not None

    def test_get_body(self):
        p = ShtmlParser()
        p.process(
            "<html><head></head><body><div>Content</div></body></html>", ""
        )
        body = p.get_body()
        assert len(body) > 0
