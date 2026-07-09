"""Extra tests for :mod:`pytigon_lib.schparser.parser`."""
import io

import pytest

from pytigon_lib.schparser.parser import (
    Elem,
    Parser,
    Script,
    content_tostring,
    tostring,
)


class TestParserExtra:
    def test_init_attributes(self):
        p = Parser()
        assert p._tree is None
        assert p._cur_elem is None

    def test_handle_starttag(self):
        p = Parser()
        p.handle_starttag("div", {"class": "main"})

    def test_handle_data(self):
        p = Parser()
        p.handle_data("some text")

    def test_handle_endtag(self):
        p = Parser()
        p.handle_endtag("div")

    def test_close_resets(self):
        p = Parser()
        p._tree = "something"
        p.close()
        assert p._tree is None

    def test_from_html_simple(self):
        tree = Parser.from_html("<div></div>")
        assert tree is not None

    def test_from_html_complex(self):
        tree = Parser.from_html("<div><p>Hello <b>World</b></p></div>")
        assert tree is not None

    def test_init_empty_string(self):
        p = Parser()
        p.init("")
        assert p._tree is None

    def test_feed_empty_string(self):
        p = Parser()
        p.feed("")

    def test_crawl_tree_sets_cur_elem(self):
        p = Parser()
        tree = Parser.from_html("<div></div>")
        p._crawl_tree(tree)
        assert True


class TestTostringExtra:
    def test_tostring_with_text(self):
        tree = Parser.from_html("<p>Hello World</p>")
        result = tostring(tree)
        assert "Hello World" in result

    def test_tostring_nested(self):
        tree = Parser.from_html("<div><span>text</span></div>")
        result = tostring(tree)
        assert "div" in result.lower()

    def test_content_tostring_empty(self):
        tree = Parser.from_html("<p></p>")
        result = content_tostring(tree)
        assert isinstance(result, str)

    def test_content_tostring_with_child_elements(self):
        tree = Parser.from_html("<p>Before <em>middle</em> After</p>")
        result = content_tostring(tree)
        assert "Before" in result
        assert "em" in result


class TestElemExtra:
    def test_str_cached(self):
        tree = Parser.from_html("<div></div>")
        e = Elem(tree)
        s1 = str(e)
        s2 = str(e)
        assert s1 == s2

    def test_len_cached(self):
        tree = Parser.from_html("<div>hello</div>")
        e = Elem(tree)
        l1 = len(e)
        l2 = len(e)
        assert l1 == l2

    def test_super_strip_empty(self):
        e = Elem(None)
        assert e.super_strip("") == ""

    def test_super_strip_only_spaces(self):
        e = Elem(None)
        assert e.super_strip("   ") == ""

    def test_super_strip_tabs(self):
        e = Elem(None)
        assert e.super_strip("\t\tHello\t\t") == "Hello"

    def test_super_strip_literal_newlines(self):
        e = Elem(None)
        assert e.super_strip("\\n\\nHello\\n") == "Hello"

    def test_tostream_with_specified_output(self):
        tree = Parser.from_html("<span>text</span>")
        e = Elem(tree)
        buf = io.StringIO()
        result = e.tostream(output=buf)
        assert result is buf

    def test_tostream_with_none_elem_twice(self):
        e = Elem(None)
        e.tostream(output=None)

    def test_tostream_with_attributes(self):
        tree = Parser.from_html('<div class="main" id="top">text</div>')
        e = Elem(tree)
        output = e.tostream()
        result = output.getvalue()
        assert "class" in result


class TestScriptExtra:
    def test_script_str(self):
        tree = Parser.from_html("<script>var x = 1;</script>")
        s = Script(tree)
        result = str(s)
        assert isinstance(result, str)

    def test_script_len(self):
        tree = Parser.from_html("<script>code</script>")
        s = Script(tree)
        assert len(s) >= 0

    def test_script_bool(self):
        s = Script(None)
        assert bool(s) is False

    def test_script_instance_is_elem(self):
        s = Script(None)
        assert isinstance(s, Elem)


class TestParserCustomSubclass:
    def test_custom_crawler(self):
        class TagCollector(Parser):
            def __init__(self):
                super().__init__()
                self.collected = []

            def handle_starttag(self, tag, attrib):
                self.collected.append(("start", tag))

            def handle_endtag(self, tag):
                self.collected.append(("end", tag))

            def handle_data(self, txt):
                if txt.strip():
                    self.collected.append(("data", txt.strip()))

        p = TagCollector()
        p.feed("<div id='main'><p>Hello</p></div>")
        assert len(p.collected) > 0
        start_tags = [e for e in p.collected if e[0] == "start"]
        assert ("start", "div") in start_tags
        assert ("start", "p") in start_tags

    def test_custom_parser_with_invalid_html(self):
        class SilentParser(Parser):
            pass

        p = SilentParser()
        p.feed("<<<not valid html>>>")

    def test_generate_starttag_text_caching(self):
        p = Parser()
        tree = Parser.from_html("<div class='x'></div>")
        p._cur_elem = tree
        text1 = p.get_starttag_text()
        text2 = p.get_starttag_text()
        assert text1 == text2

    def test_super_strip_mixed_whitespace(self):
        e = Elem(None)
        result = e.super_strip("\t Hello  \t World \t")
        assert result == "Hello World"
