"""Extra tests for :mod:`pytigon_lib.schhtml.css`."""
from unittest.mock import MagicMock

import pytest

from pytigon_lib.schhtml.css import comment_remover, Css, CssPos


class TestCommentRemoverExtra:
    def test_no_comments(self):
        result = comment_remover("body { color: red; }")
        assert result == "body { color: red; }"

    def test_only_single_line_comment(self):
        result = comment_remover("// just a comment")
        assert result.strip() == ""

    def test_only_block_comment(self):
        result = comment_remover("/* just a comment */")
        assert result.strip() == ""

    def test_mixed_comments(self):
        result = comment_remover(
            "body { /* block */ color: red; // line */ }"
        )
        assert "block" not in result

    def test_preserves_escaped_quotes_in_strings(self):
        result = comment_remover("content: 'it\\'s okay';")
        assert "it\\'s okay" in result

    def test_preserves_escaped_quotes_double(self):
        result = comment_remover('content: "say \\"hello\\"";')
        assert '\\"hello\\"' in result

    def test_block_comment_inside_rule(self):
        result = comment_remover("p { /* hidden */ margin: 0; /* also hidden */ padding: 1; }")
        assert "margin: 0" in result
        assert "padding: 1" in result
        assert "hidden" not in result

    def test_multiple_single_line_comments(self):
        result = comment_remover("// c1\na:1;// c2\nb:2;")
        assert "c1" not in result
        assert "c2" not in result
        assert "a:1" in result
        assert "b:2" in result

    def test_preserves_content_between_comments(self):
        result = comment_remover("color: red; /* comment */ margin: 0;")
        assert "color: red" in result
        assert "margin: 0" in result


class TestCssPosExtra:
    def test_key_returns_tag(self):
        pos = CssPos(["div"], {"color": "red"})
        assert pos.key() == "div"

    def test_nested_parents(self):
        pos = CssPos(["html", "body", "div"], {"color": "red"})
        assert "body" in pos.parents
        assert isinstance(pos.parents["body"], CssPos)

    def test_extend_existing_parent(self):
        pos = CssPos(["level1", "level2"], {"a": "1"})
        pos.extend(["level1", "level2"], {"b": "2"})

    def test_extend_new_parent(self):
        pos = CssPos(["level1", "level2"], {"a": "1"})
        pos.extend(["level1", "level3"], {"c": "3"})
        assert "level3" in pos.parents

    def test_extend_empty_line(self):
        pos = CssPos(["div"], {"a": "1"})
        pos.extend([], {"b": "2"})
        assert pos.attrs == {"a": "1", "b": "2"}

    def test_get_dict_no_obj(self):
        pos = CssPos(["div"], {"color": "red"})
        assert pos.get_dict(None) == {"color": "red"}

    def test_test_print_does_not_crash(self):
        pos = CssPos(["div"], {"color": "red"})
        pos.test_print(0)


class TestCssExtra:
    def test_init_empty(self):
        css = Css()
        assert css.csspos_dict == {}
        assert css._act_dict == {}
        assert css._act_keys == []

    def test_parse_indent_str_single_rule(self):
        css = Css()
        css.parse_indent_str("div\n  color: red")
        assert "div" in css.csspos_dict

    def test_parse_indent_str_multiple_attrs(self):
        css = Css()
        css.parse_indent_str("div\n  color: red\n  margin: 0")
        assert "div" in css.csspos_dict

    def test_parse_indent_str_skips_empty_lines(self):
        css = Css()
        css.parse_indent_str("div\n\n  color: red")
        assert "div" in css.csspos_dict

    def test_parse_indent_str_skips_comment_lines(self):
        css = Css()
        css.parse_indent_str("div\n  // comment\n  color: red")
        assert "div" in css.csspos_dict

    def test_parse_indent_str_multiple_selectors_comma(self):
        css = Css()
        css.parse_indent_str("div, span\n  color: red")
        assert len(css.csspos_dict) >= 1

    def test_parse_str_simple(self):
        css = Css()
        css.parse_str("div { color: red; }")
        assert "div" in css.csspos_dict

    def test_parse_str_multiple_rules(self):
        css = Css()
        css.parse_str("div { color: red; } span { margin: 0; }")
        assert len(css.csspos_dict) >= 1

    def test_parse_str_with_comments(self):
        css = Css()
        css.parse_str("div { /* comment */ color: red; }")
        assert "div" in css.csspos_dict

    def test_parse_str_empty(self):
        css = Css()
        css.parse_str("")
        assert css.csspos_dict == {}

    def test_parse_indent_str_empty(self):
        css = Css()
        css.parse_indent_str("")
        assert css.csspos_dict == {}

    def test_parse_indent_multilevel(self):
        css = Css()
        css.parse_indent_str("body\n  color: black\np\n  color: blue")
        assert len(css.csspos_dict) >= 1

    def test_handle_section_empty_content(self):
        css = Css()
        css._handle_section("div")
        assert css._act_keys == []

    def test_get_dict_returns_dict(self):
        css = Css()
        css.parse_str("div { color: red; }")
        result = css.get_dict(None)
        assert isinstance(result, dict)

    def test_test_print_does_not_crash(self):
        css = Css()
        css.parse_str("div { color: red; }")
        css.test_print()

    def test_append_keys_skips_empty(self):
        css = Css()
        css._act_keys = []
        css._act_dict = {"x": "1"}
        css._append_keys()
        assert css._act_dict == {}

    def test_strip_list(self):
        css = Css()
        result = css._strip_list([" a ", " b "])
        assert result == ["a", "b"]

    def test_parse_str_without_value(self):
        css = Css()
        css.parse_str("div { width; }")
        assert "div" in css.csspos_dict
