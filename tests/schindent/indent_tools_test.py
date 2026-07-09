"""Tests for :mod:`pytigon_lib.schindent.indent_tools`."""
import io
from unittest.mock import patch

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


class TestConvertStrings:
    def test_simple_lines(self):
        lines = io.StringIO("line1\nline2\nline3")
        result = list(_convert_strings(lines))
        assert result == ["line1", "line2", "line3"]

    def test_triple_quoted_multiline(self):
        lines = io.StringIO('x = """\nline1\nline2\n"""\n')
        result = list(_convert_strings(lines))
        assert len(result) >= 1

    def test_triple_quoted_single_line(self):
        lines = io.StringIO('x = """hello"""\n')
        result = list(_convert_strings(lines))
        assert result == ['x = """hello"""']

    def test_empty_stream(self):
        lines = io.StringIO("")
        result = list(_convert_strings(lines))
        assert result == []


class TestCountLeadingSpaces:
    def test_four_spaces(self):
        assert count_leading_spaces("    code") == 4

    def test_no_spaces(self):
        assert count_leading_spaces("code") == 0

    def test_empty_string(self):
        assert count_leading_spaces("") == 0

    def test_tabs_not_counted(self):
        assert count_leading_spaces("\tcode") == 0

    def test_all_spaces(self):
        assert count_leading_spaces("    ") == 4


class TestNormTab:
    def test_simple(self):
        stream = io.StringIO("def hello():\n    print('world')\n")
        result = norm_tab(stream)
        assert len(result) == 2
        assert result[0][0] == 0
        assert result[1][0] == 1

    def test_empty_lines_skipped(self):
        stream = io.StringIO("line1\n\nline2\n")
        result = norm_tab(stream)
        assert len(result) == 2

    def test_tab_conversion(self):
        stream = io.StringIO("def a():\n\tpass\n")
        result = norm_tab(stream)
        assert result[1][0] == 1

    def test_complex_indentation(self):
        stream = io.StringIO("a\n  b\n    c\n  d\n")
        result = norm_tab(stream)
        assert result[0][0] == 0
        assert result[1][0] == 1
        assert result[2][0] == 2
        assert result[3][0] == 1

    def test_only_whitespace_lines(self):
        stream = io.StringIO("   \n   \n")
        result = norm_tab(stream)
        assert len(result) == 0


class TestReformatJs:
    def test_def_to_function(self):
        code = [(0, "def hello():"), (1, "return 1")]
        result = reformat_js(code)
        assert "function " in result[0][1]

    def test_colon_to_brace(self):
        code = [(0, "if True:"), (1, "x = 1")]
        result = reformat_js(code)
        assert "{" in result[0][1]

    def test_empty_code(self):
        result = reformat_js([])
        assert len(result) == 1

    def test_complex(self):
        code = [(0, "def foo(x, y):"), (1, "if x > y:"), (2, "return x"), (1, "return y")]
        result = reformat_js(code)
        assert len(result) > 0

    def test_tuple_end(self):
        code = [(0, "x = ("), (1, "1"), (1, "2"), (0, ")")]
        result = reformat_js(code)
        assert len(result) > 0


class TestFileNormTab:
    def test_basic(self):
        fin = io.StringIO("def a():\n    pass\n")
        fout = io.StringIO()
        assert file_norm_tab(fin, fout) is True
        assert "pass" in fout.getvalue()

    def test_none_streams(self):
        assert file_norm_tab(None, io.StringIO()) is False
        assert file_norm_tab(io.StringIO(), None) is False
        assert file_norm_tab(None, None) is False


class TestConvertJs:
    def test_basic(self):
        fin = io.StringIO("def hello():\n    return 1\n")
        fout = io.StringIO()
        assert convert_js(fin, fout) is True
        output = fout.getvalue()
        assert "function" in output

    def test_none_streams(self):
        assert convert_js(None, io.StringIO()) is False
        assert convert_js(io.StringIO(), None) is False


class TestNormParser:
    def test_process_simple(self):
        result = norm_html("<p>Hello</p>")
        assert "p" in result

    def test_process_with_attrs(self):
        result = norm_html("<p>hello</p>")
        assert "p" in result

    def test_indent_html_simple(self):
        result = indent_html("<div><p>test</p></div>")
        assert "div" in result

    def test_norm_parser_init(self):
        p = NormParser()
        assert p.txt is not None
        assert p.tab == 0

    def test_indent_html_parser_init(self):
        p = IndentHtmlParser()
        assert p.txt is not None


class TestNormHtml:
    def test_returns_string(self):
        result = norm_html("<p>hello</p>")
        assert isinstance(result, str)

    def test_contains_tag(self):
        result = norm_html("<p>hello</p>")
        assert "p" in result


class TestIndentHtml:
    def test_returns_string(self):
        result = indent_html("<p>hello</p>")
        assert isinstance(result, str)

    def test_contains_tag(self):
        result = indent_html("<div><p>hi</p></div>")
        assert "div" in result or "p" in result

    def test_invalid_html_fallback(self):
        result = indent_html("{ not valid html }")
        assert isinstance(result, str)
