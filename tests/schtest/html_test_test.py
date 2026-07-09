"""Tests for :mod:`pytigon_lib.schtest.html_test`."""
import os
import tempfile

from pytigon_lib.schtest.html_test import extract_body_content, html_content_cmp


class TestExtractBodyContent:
    def test_extracts_body(self):
        html = "<html><head></head><body><p>Hello</p></body></html>"
        assert extract_body_content(html) == "<p>Hello</p>"

    def test_body_with_multiline(self):
        html = "<html><body>\n<p>Line1</p>\n<p>Line2</p>\n</body></html>"
        assert extract_body_content(html) == "\n<p>Line1</p>\n<p>Line2</p>\n"

    def test_no_body_returns_original(self):
        html = "<div><p>No body</p></div>"
        assert extract_body_content(html) == "<div><p>No body</p></div>"

    def test_empty_body(self):
        html = "<html><body></body></html>"
        assert extract_body_content(html) == ""

    def test_body_with_attributes(self):
        html = '<html><body class="main"><p>Content</p></body></html>'
        result = extract_body_content(html)
        assert 'Content' in result

    def test_multiple_body_tags_uses_first(self):
        html = "<body>First</body><body>Second</body>"
        assert extract_body_content(html) == "First"


class TestHtmlContentCmp:
    def test_identical_files(self):
        content1 = "<html><body><p>Same</p></body></html>"
        content2 = "<html><body><p>Same</p></body></html>"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f1:
            f1.write(content1)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f2:
            f2.write(content2)
        try:
            assert html_content_cmp(f1.name, f2.name) is True
        finally:
            os.unlink(f1.name)
            os.unlink(f2.name)

    def test_different_body(self):
        content1 = "<html><body><p>A</p></body></html>"
        content2 = "<html><body><p>B</p></body></html>"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f1:
            f1.write(content1)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f2:
            f2.write(content2)
        try:
            assert html_content_cmp(f1.name, f2.name) is False
        finally:
            os.unlink(f1.name)
            os.unlink(f2.name)

    def test_different_head_same_body(self):
        content1 = '<html><head><title>A</title></head><body><p>Same</p></body></html>'
        content2 = '<html><head><title>B</title></head><body><p>Same</p></body></html>'
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f1:
            f1.write(content1)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f2:
            f2.write(content2)
        try:
            assert html_content_cmp(f1.name, f2.name) is True
        finally:
            os.unlink(f1.name)
            os.unlink(f2.name)

    def test_no_body_tag_compares_full_content(self):
        content1 = "<div>A</div>"
        content2 = "<div>A</div>"
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f1:
            f1.write(content1)
        with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f2:
            f2.write(content2)
        try:
            assert html_content_cmp(f1.name, f2.name) is True
        finally:
            os.unlink(f1.name)
            os.unlink(f2.name)
