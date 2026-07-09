"""Tests for :mod:`pytigon_lib.schindent.indent_style` utility functions."""

import io
import tempfile
import os

import pytest

from pytigon_lib.schindent.indent_style import (
    _get_elem,
    _pre_process_line,
    _space_count,
    _status_close,
    _transform_elem,
    list_with_next_generator,
    translate,
)


class TestListWithNextGenerator:
    def test_three_items(self):
        result = list(list_with_next_generator(["a", "b", "c"]))
        assert result == [("a", "b"), ("b", "c"), ("c", None)]

    def test_single_item(self):
        result = list(list_with_next_generator(["x"]))
        assert result == [("x", None)]

    def test_two_items(self):
        result = list(list_with_next_generator([1, 2]))
        assert result == [(1, 2), (2, None)]

    def test_empty_returns_nothing(self):
        result = list(list_with_next_generator([]))
        assert result == []

    def test_mixed_types(self):
        result = list(list_with_next_generator([1, "two", 3.0]))
        assert len(result) == 3
        assert result[-1] == (3.0, None)


class TestTranslate:
    def test_identity(self):
        assert translate("hello") == "hello"

    def test_empty_string(self):
        assert translate("") == ""

    def test_polish(self):
        assert translate("Zażółć") == "Zażółć"


class TestSpaceCount:
    def test_no_spaces(self):
        assert _space_count("hello") == 0

    def test_four_spaces(self):
        assert _space_count("    hello") == 4

    def test_all_spaces(self):
        assert _space_count("     ") == 5

    def test_empty_string(self):
        assert _space_count("") == 0

    def test_tab_not_counted_as_space(self):
        assert _space_count("\thello") == 0


class TestGetElem:
    def test_simple_tag(self):
        assert _get_elem("div") == "div"

    def test_tag_with_attrs(self):
        assert _get_elem("div class=foo id=bar") == "div"

    def test_tag_with_leading_spaces(self):
        assert _get_elem("  span") == "span"

    def test_empty_string(self):
        assert _get_elem("") == ""

    def test_tag_with_camel_case(self):
        assert _get_elem("MyComponent class=foo") == "MyComponent"


class TestTransformElem:
    def test_no_attrs(self):
        assert _transform_elem("div") == "div"

    def test_single_attr(self):
        result = _transform_elem("div class=foo")
        assert result == 'div class="foo"'

    def test_multiple_attrs(self):
        result = _transform_elem("div class=foo,,,id=bar")
        assert 'class="foo"' in result
        assert 'id="bar"' in result

    def test_attr_without_equals(self):
        result = _transform_elem("input disabled,,,type=text")
        assert " disabled" in result
        assert 'type="text"' in result

    def test_element_with_only_whitespace(self):
        result = _transform_elem("span ")
        assert "span" in result


class TestPreProcessLine:
    def test_empty_line(self):
        result = _pre_process_line("   ")
        assert result == [None]

    def test_text_line(self):
        result = _pre_process_line(".text content")
        assert result[0] is not None
        assert result[0][2] == "text content"

    def test_non_tag_line(self):
        result = _pre_process_line("# comment")
        assert result[0] is not None
        assert result[0][2] == "# comment"

    def test_html_element(self):
        result = _pre_process_line("div class=foo")
        assert result[0] is not None
        assert 'class="foo"' in result[0][1]

    def test_element_with_html_part(self):
        result = _pre_process_line("div...some html")
        assert result[0] is not None
        assert result[0][2] == "some html"

    def test_element_with_code_and_html(self):
        result = _pre_process_line("div class=foo...<span>text</span>")
        assert result[0] is not None
        assert '<span>text</span>' in str(result[0][2])

    def test_multi_element_colons(self):
        result = _pre_process_line("div::span")
        assert len(result) >= 1

    def test_template_line(self):
        result = _pre_process_line("% if user")
        assert result[0] is not None
        assert "%" in str(result[0][1])


class TestStatusClose:
    def test_status_0(self):
        result = _status_close(0, (0, "div", "text", 0), (0, None, None, 0))
        assert result == 0

    def test_status_2(self):
        result = _status_close(2, (0, "div", "text", 2), (0, None, None, 0))
        assert result == 0

    def test_status_1(self):
        result = _status_close(1, (0, "div", "text", 1), (0, None, None, 0))
        assert result == 1

    def test_status_3(self):
        result = _status_close(3, (0, "div", "text", 3), (0, None, None, 0))
        assert result == 2

    def test_status_4_deeper_next(self):
        line = (0, "div", "text", 4)
        next_line = (1, "span", "text", 0)
        result = _status_close(4, line, next_line)
        assert result == 3

    def test_status_4_same_level(self):
        line = (0, "div", "text", 4)
        next_line = (0, "span", "text", 0)
        result = _status_close(4, line, next_line)
        assert result == 1
