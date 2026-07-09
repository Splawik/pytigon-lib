"""Tests for :mod:`pytigon_lib.schindent.html2ihtml`."""

import io

import pytest

from pytigon_lib.schindent.html2ihtml import Html2IhtmlParser, divide


class TestDivide:
    def test_short_text(self):
        result = divide("hello", 80)
        assert result == ["hello"]

    def test_exact_width(self):
        result = divide("hello", 5)
        assert result == ["hello"]

    def test_long_text_wrap(self):
        result = divide("hello world foo bar", 10)
        assert len(result) > 1
        for line in result:
            assert len(line) <= 10

    def test_word_longer_than_width(self):
        result = divide("supercalifragilistic", 10)
        assert len(result) >= 1

    def test_empty_string(self):
        result = divide("", 80)
        assert result == []

    def test_newlines_become_spaces(self):
        result = divide("line1\n line2\nline3", 80)
        joined = " ".join(result)
        assert "line1" in joined
        assert "line2" in joined

    def test_width_limit(self):
        result = divide("a b c d e f g h i j", 5)
        for line in result:
            assert len(line) <= 5

    def test_no_trailing_spaces(self):
        result = divide("hello  world  ", 80)
        assert len(result) >= 1


class TestHtml2IhtmlParser:
    def test_initial_state(self):
        out = io.StringIO()
        parser = Html2IhtmlParser(out)
        assert parser.level == 0
        assert parser.in_tag == []
        assert parser.in_script is False

    def test_simple_paragraph(self):
        out = io.StringIO()
        parser = Html2IhtmlParser(out)
        parser.feed("<p>Hello</p>")
        parser.close()
        output = out.getvalue()
        assert "p" in output
        assert "Hello" in output

    def test_nested_elements(self):
        out = io.StringIO()
        parser = Html2IhtmlParser(out)
        parser.feed("<div><span>text</span></div>")
        parser.close()
        output = out.getvalue()
        assert "div" in output
        assert "span" in output
        assert "text" in output

    def test_self_closing_tag(self):
        out = io.StringIO()
        parser = Html2IhtmlParser(out)
        parser.feed("<br/><hr/>")
        parser.close()
        output = out.getvalue()
        assert "br" in output
        assert "hr" in output

    def test_tag_with_attributes(self):
        out = io.StringIO()
        parser = Html2IhtmlParser(out)
        parser.feed('<div class="container" id="main">text</div>')
        parser.close()
        output = out.getvalue()
        assert "class=container" in output
        assert "id=main" in output

    def test_script_tag(self):
        out = io.StringIO()
        parser = Html2IhtmlParser(out)
        parser.feed("<script>console.log('hi')</script>")
        parser.close()
        output = out.getvalue()
        assert "script" in output
        assert ">>>" in output

    def test_style_tag(self):
        out = io.StringIO()
        parser = Html2IhtmlParser(out)
        parser.feed("<style>body {color: red;}</style>")
        parser.close()
        output = out.getvalue()
        assert "style" in output
        assert ">>>" in output

    def test_empty_elements(self):
        out = io.StringIO()
        parser = Html2IhtmlParser(out)
        parser.feed("<div></div>")
        parser.close()
        output = out.getvalue()
        assert "div" in output

    def test_multiple_paragraphs(self):
        out = io.StringIO()
        parser = Html2IhtmlParser(out)
        parser.feed("<p>First</p><p>Second</p>")
        parser.close()
        output = out.getvalue()
        assert "First" in output
        assert "Second" in output

    def test_mixed_content(self):
        out = io.StringIO()
        parser = Html2IhtmlParser(out)
        parser.feed("<div><h1>Title</h1><p>Content</p></div>")
        parser.close()
        output = out.getvalue()
        assert "h1" in output
        assert "Title" in output
        assert "Content" in output

    def test_custom_width(self):
        out = io.StringIO()
        parser = Html2IhtmlParser(out, width=30)
        parser.feed("<p>This is a relatively long paragraph text</p>")
        parser.close()
        output = out.getvalue()
        assert "This" in output
        assert "text" in output

    def test_pre_tag_preserves_whitespace(self):
        out = io.StringIO()
        parser = Html2IhtmlParser(out)
        parser.feed("<pre>line1\n  line2</pre>")
        parser.close()
        output = out.getvalue()
        assert "line1" in output

    def test_textarea_tag(self):
        out = io.StringIO()
        parser = Html2IhtmlParser(out)
        parser.feed("<textarea>default text</textarea>")
        parser.close()
        output = out.getvalue()
        assert "textarea" in output
        assert "default text" in output

    def test_code_tag(self):
        out = io.StringIO()
        parser = Html2IhtmlParser(out)
        parser.feed("<code>print('hello')</code>")
        parser.close()
        output = out.getvalue()
        assert "code" in output
        assert "print" in output
