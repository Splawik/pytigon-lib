"""Extra tests for :mod:`pytigon_lib.schindent.indent_markdown`."""

import pytest

from pytigon_lib.schindent.indent_markdown import (
    REG_OBJ_RENDERER,
    BaseObjRenderer,
    IndentMarkdownProcessor,
    get_indent,
    get_obj_renderer,
    imd2html,
    markdown_to_html,
    register_obj_renderer,
    unindent,
)


class TestGetIndent:
    def test_zero_indent(self):
        assert get_indent("no indent") == 0

    def test_four_spaces(self):
        assert get_indent("    indented") == 4

    def test_two_spaces(self):
        assert get_indent("  small") == 2

    def test_tab(self):
        assert get_indent("\twith tab") == 1

    def test_empty_string(self):
        assert get_indent("") == 0

    def test_mixed_whitespace(self):
        result = get_indent("  \t content")
        assert result == 4


class TestUnindent:
    def test_removes_common_indent(self):
        result = unindent(["    line1", "    line2"])
        assert result == ["line1", "line2"]

    def test_empty_list(self):
        result = unindent([])
        assert result == []

    def test_no_indent(self):
        result = unindent(["no indent"])
        assert result == ["no indent"]

    def test_empty_lines_present(self):
        result = unindent(["", "    indented", ""])
        assert "indented" in result[1]

    def test_mixed_indent_uses_first_nonempty(self):
        result = unindent(["    deep", "  shallow", ""])
        assert result[0] == "deep"


class TestMarkdownToHtmlExtra:
    def test_blockquote(self):
        result = markdown_to_html("> quote")
        assert "quote" in result

    def test_horizontal_rule(self):
        result = markdown_to_html("---")
        assert isinstance(result, str)


class TestIndentMarkdownProcessorExtra:
    def test_get_root_returns_self(self):
        p = IndentMarkdownProcessor()
        assert p.get_root() is p

    def test_get_root_with_parent(self):
        parent = IndentMarkdownProcessor()
        child = IndentMarkdownProcessor(parent_processor=parent)
        assert child.get_root() is parent

    def test_get_root_deep_nesting(self):
        root = IndentMarkdownProcessor()
        child = IndentMarkdownProcessor(parent_processor=root)
        grandchild = IndentMarkdownProcessor(parent_processor=child)
        assert grandchild.get_root() is root

    def test_json_dumps_simple(self):
        p = IndentMarkdownProcessor()
        result = p._json_dumps({"key": "value"})
        assert '"key"' in result

    def test_json_dumps_escapes_newlines(self):
        p = IndentMarkdownProcessor()
        result = p._json_dumps({"key": "a\nb"})
        assert "\\n" in result

    def test_json_loads_dict_string(self):
        p = IndentMarkdownProcessor()
        result = p._json_loads('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_loads_non_json(self):
        p = IndentMarkdownProcessor()
        result = p._json_loads("plain text")
        assert result == "plain text"

    def test_json_loads_empty(self):
        p = IndentMarkdownProcessor()
        result = p._json_loads("")
        assert result == ""

    def test_json_loads_restores_newlines(self):
        p = IndentMarkdownProcessor()
        result = p._json_loads('{"key": "a\\nb"}')
        assert isinstance(result, dict)

    def test_init_with_uri(self):
        p = IndentMarkdownProcessor(uri="test://uri")
        assert p.uri == "test://uri"

    def test_init_with_line_number(self):
        p = IndentMarkdownProcessor(line_number=42)
        assert p.line_number == 42

    def test_init_all_params(self):
        p = IndentMarkdownProcessor(
            output_format="pdf",
            parent_processor=None,
            uri="/test",
            line_number=10,
        )
        assert p.output_format == "pdf"
        assert p.uri == "/test"
        assert p.line_number == 10

    def test_convert_empty_source(self):
        p = IndentMarkdownProcessor()
        result = p.convert("")
        assert isinstance(result, str)

    def test_render_wiki_calls_markdown_to_html(self):
        p = IndentMarkdownProcessor()
        result = p.render_wiki("# Test")
        assert isinstance(result, str)

    def test_named_renderers_initially_empty(self):
        p = IndentMarkdownProcessor()
        assert p.named_renderers == {}

    def test_lines_initially_none(self):
        p = IndentMarkdownProcessor()
        assert p.lines is None

    def test_imd2html_returns_html(self):
        result = imd2html("# Hello\nWorld")
        assert isinstance(result, str)
        assert "Hello" in result


class TestBaseObjRendererExtra:
    def test_init_defaults(self):
        r = BaseObjRenderer()
        assert r.extra_info == ""
        assert r.line_number == 0

    def test_init_with_extra_info(self):
        r = BaseObjRenderer("my_info")
        assert r.extra_info == "my_info"

    def test_get_info_returns_dict(self):
        info = BaseObjRenderer.get_info()
        assert isinstance(info, dict)
        assert "name" in info
        assert "title" in info

    def test_get_edit_form_returns_none(self):
        r = BaseObjRenderer()
        assert r.get_edit_form() is None

    def test_convert_form_to_dict(self):
        r = BaseObjRenderer()

        class FakeForm:
            cleaned_data = {"x": 1}

        assert r.convert_form_to_dict(FakeForm()) == {"x": 1}

    def test_form_from_dict_no_param(self):
        r = BaseObjRenderer()

        class FakeForm:
            def __init__(self, initial=None):
                self.initial = initial

        result = r.form_from_dict(FakeForm)
        assert result.initial is None

    def test_form_from_dict_with_param(self):
        r = BaseObjRenderer()

        class FakeForm:
            def __init__(self, initial=None):
                self.initial = initial

        result = r.form_from_dict(FakeForm, {"x": 1})
        assert result.initial == {"x": 1}

    def test_gen_context_empty(self):
        r = BaseObjRenderer()
        result = r.gen_context(None, [], "html", None)
        assert result == {}

    def test_get_renderer_template_name(self):
        r = BaseObjRenderer()
        assert r.get_renderer_template_name() is None

    def test_get_edit_template_name(self):
        r = BaseObjRenderer()
        assert "schwiki" in r.get_edit_template_name()

    def test_get_line_number_negative(self):
        r = BaseObjRenderer()
        parent = IndentMarkdownProcessor(line_number=-1)
        assert r._get_line_number(parent) == -1


class TestRenderObjRegistration:
    def test_register_obj_renderer(self):
        class CustomRenderer(BaseObjRenderer):
            pass

        register_obj_renderer("custom", CustomRenderer)
        assert "custom" in REG_OBJ_RENDERER

    def test_get_obj_renderer_registered(self):
        class CustomRenderer(BaseObjRenderer):
            pass

        register_obj_renderer("custom2", CustomRenderer)
        obj = get_obj_renderer("custom2")
        assert isinstance(obj, CustomRenderer)

    def test_get_obj_renderer_fallback(self):
        obj = get_obj_renderer("unknown_name")
        assert isinstance(obj, BaseObjRenderer)
        assert obj.extra_info == "unknown_name"


class TestImd2html:
    def test_simple_conversion(self):
        result = imd2html("# Hello\nWorld")
        assert "Hello" in result

    def test_returns_string(self):
        result = imd2html("test")
        assert isinstance(result, str)
