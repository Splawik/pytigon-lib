"""Extra tests for :mod:`pytigon_lib.schindent.indent_tools`."""

import io

import pytest

from pytigon_lib.schindent.indent_tools import (
    _convert_strings,
    convert_js,
    count_leading_spaces,
    file_norm_tab,
    indent_html,
    IndentHtmlParser,
    norm_html,
    norm_tab,
    NormParser,
    reformat_js,
)


class TestConvertStringsExtra:
    def test_single_line_no_strings(self):
        lines = io.StringIO("hello\nworld\n")
        result = list(_convert_strings(lines))
        assert result == ["hello", "world"]

    def test_multiline_string_start_midline(self):
        lines = io.StringIO('x = """start\nmiddle\nend"""\n')
        result = list(_convert_strings(lines))
        assert len(result) == 1
        assert "start" in result[0]

    def test_no_triple_quotes(self):
        lines = io.StringIO('print("hello")\nprint("world")\n')
        result = list(_convert_strings(lines))
        assert result == ['print("hello")', 'print("world")']

    def test_multiple_multiline_strings(self):
        lines = io.StringIO('a = """one\ntwo"""\nb = """three\nfour"""\n')
        result = list(_convert_strings(lines))
        assert len(result) == 2

    def test_single_line_triple_quoted_with_newline_char(self):
        lines = io.StringIO('x = """single"""\n')
        result = list(_convert_strings(lines))
        assert result == ['x = """single"""']


class TestCountLeadingSpacesExtra:
    def test_eight_spaces(self):
        assert count_leading_spaces("        deep") == 8

    def test_one_space(self):
        assert count_leading_spaces(" x") == 1

    def test_mixed_tabs_and_spaces(self):
        assert count_leading_spaces("\t  code") == 0


class TestNormTabExtra:
    def test_code_with_triple_quoted_strings(self):
        stream = io.StringIO('x = """first\nsecond\nthird"""\n')
        result = norm_tab(stream)
        assert len(result) == 1

    def test_multiple_levels_indent(self):
        stream = io.StringIO("def a():\n    def b():\n        def c():\n            pass\n")
        result = norm_tab(stream)
        assert len(result) == 4
        assert result[0][0] == 0
        assert result[1][0] == 1
        assert result[2][0] == 2
        assert result[3][0] == 3

    def test_return_to_previous_level(self):
        stream = io.StringIO("a:\n  b:\n    c\n  d\n")
        result = norm_tab(stream)
        assert result[0][0] == 0
        assert result[1][0] == 1
        assert result[2][0] == 2
        assert result[3][0] == 1

    def test_empty_beginning_lines(self):
        stream = io.StringIO("\n\ndef a():\n    pass\n")
        result = norm_tab(stream)
        assert len(result) == 2

    def test_only_comments_or_empty(self):
        stream = io.StringIO("  \n  \n")
        result = norm_tab(stream)
        assert len(result) == 0


class TestReformatJsExtra:
    def test_if_with_colon(self):
        code = [(0, "if x:"), (1, "do_something")]
        result = reformat_js(code)
        assert "{" in result[0][1]

    def test_endswith_paren(self):
        code = [(0, "foo("), (1, "1"), (1, "2"), (0, ")")]
        result = reformat_js(code)
        assert "(" in result[0][1]

    def test_endswith_bracket(self):
        code = [(0, "x = ["), (1, "1"), (1, "2"), (0, "]")]
        result = reformat_js(code)
        assert "[" in result[0][1]

    def test_endswith_comma_bracket(self):
        code = [(0, "x = [,"), (1, "1"), (1, "2"), (0, "]")]
        result = reformat_js(code)
        assert "[" in result[0][1]

    def test_endswith_slash_colon(self):
        code = [(0, "label/:"), (1, "content")]
        result = reformat_js(code)
        assert "/:" not in result[0][1]

    def test_endswith_equal(self):
        code = [(0, "obj ="), (1, "key: val"), (0, "end")]
        result = reformat_js(code)
        assert "{" in result[0][1]

    def test_endswith_curly_open(self):
        code = [(0, "x = {"), (1, "key: val"), (0, "}")]
        result = reformat_js(code)
        assert "{" in result[0][1]

    def test_single_level_block(self):
        code = [(0, "if x:")]
        result = reformat_js(code)
        assert len(result) > 0

    def test_else_to_default(self):
        code = [(0, "if x:"), (0, "else:")]
        result = reformat_js(code)
        assert len(result) > 0


class TestFileNormTabExtra:
    def test_with_empty_content(self):
        fin = io.StringIO("")
        fout = io.StringIO()
        assert file_norm_tab(fin, fout) is True
        assert fout.getvalue() == ""


class TestConvertJsExtra:
    def test_cleans_double_semicolons(self):
        fin = io.StringIO("x:\n  y\n")
        fout = io.StringIO()
        assert convert_js(fin, fout) is True
        assert ";;" not in fout.getvalue()

    def test_cleans_brace_semicolons(self):
        fin = io.StringIO("if x:\n  y\n")
        fout = io.StringIO()
        assert convert_js(fin, fout) is True
        assert "};" not in fout.getvalue()


class TestNormParserExtra:
    def test_remove_spaces(self):
        p = NormParser()
        assert p._remove_spaces("  hello  ") == "hello"
        assert p._remove_spaces("") == ""
        assert p._remove_spaces("no_spaces") == "no_spaces"

    def test_print_attr_with_value(self):
        p = NormParser()
        result = p._print_attr({"href": "http://example.com", "class": "main"})

    def test_print_attr_boolean(self):
        p = NormParser()
        result = p._print_attr({"disabled": ""})
        assert "disabled" in result

    def test_print_attr_empty(self):
        p = NormParser()
        result = p._print_attr({})
        assert result == ""

    def test_print_attr_non_string(self):
        p = NormParser()
        result = p._print_attr({"width": 100})
        assert "100" in result

    def test_handle_startendtag(self):
        p = NormParser()
        p.handle_startendtag("br", {"clear": "all"})
        assert p.txt is not None

    def test_process_with_data(self):
        p = NormParser()
        result = p.process("<p>Hello World</p>")
        assert "Hello World" in result

    def test_process_compact(self):
        p = NormParser()
        result = p.process("<div><span>text</span></div>")
        assert "div" in result


class TestIndentHtmlParserExtra:
    def test_init(self):
        p = IndentHtmlParser()
        assert p.txt is not None
        assert p.tab == 0

    def test_handle_starttag_indentation(self):
        p = IndentHtmlParser()
        p.handle_starttag("div", {})
        assert p.tab == 1

    def test_handle_endtag_indentation(self):
        p = IndentHtmlParser()
        p.handle_starttag("div", {})
        p.handle_endtag("div")
        assert p.tab == 0

    def test_handle_endtag_never_negative(self):
        p = IndentHtmlParser()
        p.handle_endtag("div")
        assert p.tab == 0

    def test_handle_data_whitespace_only(self):
        p = IndentHtmlParser()
        p.handle_data("   \n  \t  ")
        assert True

    def test_handle_starttag_output_format(self):
        p = IndentHtmlParser()
        p.handle_starttag("div", {"class": "main"})
        output = p.txt.getvalue()
        assert len(output) > 0


class TestNormHtmlExtra:
    def test_empty_string(self):
        result = norm_html("")
        assert isinstance(result, str)

    def test_self_closing_tag(self):
        result = norm_html("<br/>")
        assert isinstance(result, str)

    def test_nested_tags(self):
        result = norm_html("<div><p><span>text</span></p></div>")
        assert "div" in result


class TestIndentHtmlExtra:
    def test_empty_string(self):
        result = indent_html("")
        assert isinstance(result, str)

    def test_single_line_element(self):
        result = indent_html("<p>hello</p>")
        assert "p" in result
        assert "hello" in result
