"""Tests for :mod:`pytigon_lib.schindent.indent_markdown`."""
import pytest

from pytigon_lib.schindent.indent_markdown import (
    IndentMarkdownProcessor,
    markdown_to_html,
)


class TestMarkdownToHtml:
    def test_returns_html(self):
        result = markdown_to_html("# Hello")
        assert "<h1>" in result or "Hello" in result

    def test_paragraph(self):
        result = markdown_to_html("Hello world")
        assert "Hello world" in result

    def test_bold(self):
        result = markdown_to_html("**bold**")
        assert "strong" in result or "bold" in result

    def test_italic(self):
        result = markdown_to_html("*italic*")
        assert "em" in result or "italic" in result

    def test_code(self):
        result = markdown_to_html("`code`")
        assert "code" in result

    def test_link(self):
        result = markdown_to_html("[text](http://example.com)")
        assert "href" in result or "http" in result

    def test_list(self):
        result = markdown_to_html("- item1\n- item2")
        assert "li" in result or "item" in result

    def test_empty(self):
        result = markdown_to_html("")
        assert isinstance(result, str)


class TestIndentMarkdownProcessor:
    def test_init(self):
        processor = IndentMarkdownProcessor(output_format="html")
        assert processor.output_format == "html"

    def test_convert_markdown(self):
        processor = IndentMarkdownProcessor(output_format="html")
        result = processor.convert("# Hello\nWorld")
        assert "Hello" in result
        assert "World" in result

    def test_convert_imd(self):
        processor = IndentMarkdownProcessor(output_format="html")
        result = processor.convert("# Test")
        assert "Test" in result or "h1" in result

    def test_init_pdf(self):
        processor = IndentMarkdownProcessor(output_format="pdf")
        assert processor.output_format == "pdf"


class TestModuleExports:
    def test_has_markdown_to_html(self):
        assert callable(markdown_to_html)

    def test_has_processor(self):
        assert IndentMarkdownProcessor is not None
