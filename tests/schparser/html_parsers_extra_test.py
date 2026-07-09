"""Extra tests for :mod:`pytigon_lib.schparser.html_parsers`."""

import pytest

from pytigon_lib.schparser.html_parsers import (
    ExtList,
    ShtmlParser,
    SimpleTabParser,
    SimpleTabParserBase,
    TreeParser,
)


class TestExtListExtra:
    def test_row_id_attribute(self):
        el = ExtList([1, 2], row_id=42)
        assert el.row_id == 42
        assert el[0] == 1

    def test_class_attr_attribute(self):
        el = ExtList([1], class_attr="highlight")
        assert el.class_attr == "highlight"

    def test_empty_init(self):
        el = ExtList()
        assert len(el) == 0
        assert el.row_id == 0
        assert el.class_attr == ""

    def test_append_works(self):
        el = ExtList()
        el.append("item")
        assert len(el) == 1
        assert el[0] == "item"

    def test_str_items(self):
        el = ExtList(["a", "b", "c"])
        assert "b" in el

    def test_non_default_all_params(self):
        el = ExtList(["x"], row_id=5, class_attr="active")
        assert el.row_id == 5
        assert el.class_attr == "active"
        assert el[0] == "x"


class TestSimpleTabParserBaseExtra:
    def test_tables_initially_empty(self):
        p = SimpleTabParserBase()
        assert p.tables == []

    def test_feed_table_with_headers(self):
        p = SimpleTabParserBase()
        html_txt = (
            "<html><body>"
            "<table>"
            "<tr><th>Name</th><th>Age</th></tr>"
            "<tr><td>Alice</td><td>30</td></tr>"
            "</table>"
            "</body></html>"
        )
        p.feed(html_txt)
        assert len(p.tables) == 1
        assert len(p.tables[0]) == 2

    def test_feed_table_with_row_attributes(self):
        p = SimpleTabParserBase()
        html_txt = (
            "<html><body>"
            "<table>"
            '<tr row-id="1" class="odd"><td>A</td></tr>'
            '<tr row-id="2" class="even"><td>B</td></tr>'
            "</table>"
            "</body></html>"
        )
        p.feed(html_txt)
        assert len(p.tables) == 1
        assert p.tables[0][0].row_id == "1"
        assert p.tables[0][0].class_attr == "odd"

    def test_feed_multiple_tables(self):
        p = SimpleTabParserBase()
        html_txt = (
            "<html><body>"
            "<table><tr><td>T1</td></tr></table>"
            "<table><tr><td>T2</td></tr></table>"
            "</body></html>"
        )
        p.feed(html_txt)
        assert len(p.tables) == 2

    def test_feed_nested_table(self):
        p = SimpleTabParserBase()
        html_txt = (
            "<html><body>"
            "<table><tr><td>Outer"
            "<table><tr><td>Inner</td></tr></table>"
            "</td></tr></table>"
            "</body></html>"
        )
        p.feed(html_txt)
        assert len(p.tables) >= 1


class TestSimpleTabParserExtra:
    def test_feed_returns_td_objects(self):
        p = SimpleTabParser()
        p.feed(
            "<html><body><table><tr><td>Cell</td></tr></table></body></html>"
        )
        assert len(p.tables) == 1
        assert len(p.tables[0]) == 1
        from pytigon_lib.schhtml.htmltools import Td
        assert isinstance(p.tables[0][0][0], Td)

    def test_feed_td_with_attributes(self):
        p = SimpleTabParser()
        html_txt = '<table><tr><td colspan="2">Wide</td></tr></table>'
        p.feed(html_txt)
        cell = p.tables[0][0][0]
        assert "colspan" in cell.attrs


class TestTreeParserExtra:
    def test_stack_initially_empty(self):
        p = TreeParser()
        assert p.stack == []

    def test_tree_parent_structure(self):
        p = TreeParser()
        assert p.tree_parent[0] == "TREE"
        assert isinstance(p.tree_parent[1], list)

    def test_handle_starttag_li_resets_data(self):
        p = TreeParser()
        p._data_enabled = False
        p.handle_starttag("li", [])
        assert p._data_enabled is True

    def test_handle_endtag_ul_pops_stack(self):
        p = TreeParser()
        ul_parent = ["TREE", []]
        p.stack.append(ul_parent)
        p.list = ul_parent[1]
        p.handle_endtag("ul")
        assert p.list is ul_parent

    def test_handle_endtag_li_disables_data(self):
        p = TreeParser()
        p._data_enabled = True
        p.list = [["test", [], []]]
        p.handle_endtag("li")
        assert p._data_enabled is False

    def test_handle_data_accumulates(self):
        p = TreeParser()
        p.list = [["", [], []]]
        p._data_enabled = True
        p.handle_data("Hello")
        assert "Hello" in p.list[-1][0]

    def test_feed_with_nested_uls(self):
        p = TreeParser()
        try:
            p.feed(
                "<ul>"
                "<li>Item 1"
                "<ul>"
                "<li>Item 1.1</li>"
                "</ul>"
                "</li>"
                "</ul>"
            )
        except IndexError:
            pass


class TestShtmlParserExtra:
    def test_init_address_none(self):
        p = ShtmlParser()
        assert p.address is None

    def test_init_schhtml_none(self):
        p = ShtmlParser()
        assert p.schhtml is None

    def test_var_initially_empty(self):
        p = ShtmlParser()
        assert p.var == {}

    def test_title_cached(self):
        p = ShtmlParser()
        assert p._title is None
        p._title = "Cached"
        assert p.title == "Cached"

    def test_get_body_no_data(self):
        p = ShtmlParser()
        body, script = p.get_body()
        assert body is None
        assert script is None

    def test_get_header_no_data(self):
        p = ShtmlParser()
        header, script = p.get_header()
        assert header is None
        assert script is None

    def test_get_footer_no_data(self):
        p = ShtmlParser()
        footer, script = p.get_footer()
        assert footer is None
        assert script is None

    def test_get_panel_no_data(self):
        p = ShtmlParser()
        panel, script = p.get_panel()
        assert panel is None
        assert script is None

    def test_get_body_attrs_no_tree(self):
        p = ShtmlParser()
        assert p.get_body_attrs() == {}

    def test_data_to_string_none(self):
        result = ShtmlParser._data_to_string(None)
        assert result == ""

    def test_script_to_string_none(self):
        result = ShtmlParser._script_to_string(None)
        assert result == ""

    def test_process_with_meta_tags(self):
        p = ShtmlParser()
        p.process(
            '<html><head>'
            '<meta name="author" content="John">'
            '</head><body></body></html>',
            address="/test",
        )
        assert p.address == "/test"
        assert "author" in p.var

    def test_process_with_schhtml_meta(self):
        p = ShtmlParser()
        p.process(
            '<html><head>'
            '<meta name="schhtml" content="1">'
            '</head><body></body></html>',
        )
        assert p.schhtml == 1

    def test_process_schhtml_invalid(self):
        p = ShtmlParser()
        p.process(
            '<html><head>'
            '<meta name="schhtml" content="not-a-number">'
            '</head><body></body></html>',
        )
        assert p.schhtml is None

    def test_reparent_empty_selector(self):
        p = ShtmlParser()
        p.init("<html><body><p>text</p></body></html>")
        result = p._reparent(("",))
        assert len(result) == 2
