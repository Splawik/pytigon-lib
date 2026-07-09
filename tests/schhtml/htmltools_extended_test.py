"""Tests for :mod:`pytigon_lib.schhtml.htmltools`."""
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schhtml.htmltools import (
    _SAFE_URL_SCHEMES,
    _SSRF_BLOCKED_HOSTS,
    _is_safe_url,
    superstrip,
    Td,
)


class TestIsSafeUrl:
    def test_http_allowed(self):
        assert _is_safe_url("http://example.com/path")

    def test_https_allowed(self):
        assert _is_safe_url("https://example.com/path")

    def test_ftp_blocked(self):
        assert not _is_safe_url("ftp://example.com/file")

    def test_file_blocked(self):
        assert not _is_safe_url("file:///etc/passwd")

    def test_localhost_blocked(self):
        assert not _is_safe_url("http://localhost:8000")

    def test_ip_127_blocked(self):
        assert not _is_safe_url("http://127.0.0.1:8000")

    def test_ip_0_blocked(self):
        assert not _is_safe_url("http://0.0.0.0")

    def test_private_10_blocked(self):
        assert not _is_safe_url("http://10.1.1.1")

    def test_private_192_blocked(self):
        assert not _is_safe_url("http://192.168.1.1")

    def test_private_172_blocked(self):
        assert not _is_safe_url("http://172.16.1.1")

    def test_private_172_outside_blocked(self):
        assert not _is_safe_url("http://172.31.1.1")

    def test_public_172_allowed(self):
        assert _is_safe_url("http://172.32.1.1")

    def test_link_local_blocked(self):
        assert not _is_safe_url("http://169.254.1.1")

    def test_empty_hostname(self):
        assert not _is_safe_url("http://")

    def test_no_scheme(self):
        assert not _is_safe_url("example.com")


class TestSuperstrip:
    def test_removes_extra_spaces(self):
        assert superstrip("hello    world") == "hello world"

    def test_removes_newlines(self):
        assert superstrip("hello\nworld") == "hello world"

    def test_removes_tabs(self):
        assert superstrip("hello\tworld") == "hello world"

    def test_strips_whitespace(self):
        assert superstrip("  hello  ") == "hello"

    def test_many_spaces(self):
        assert superstrip("a" + " " * 20 + "b") == "a b"

    def test_multiple_newlines(self):
        assert superstrip("a\n\n\nb") == "a b"

    def test_mixed_whitespace(self):
        assert superstrip("a \t\n\r b") == "a b"

    def test_empty_string(self):
        assert superstrip("") == ""

    def test_only_spaces(self):
        assert superstrip("   ") == ""


class TestTd:
    def test_init_defaults(self):
        td = Td("cell data")
        assert td.data == "cell data"
        assert td.attrs == {}
        assert td.children is None

    def test_init_with_attrs(self):
        td = Td("data", {"colspan": "2"})
        assert td.attrs == {"colspan": "2"}

    def test_init_with_children(self):
        td = Td("data", children=["child1"])
        assert td.children == ["child1"]

    def test_attr_property(self):
        td = Td("data")
        assert td.attr == ""

    def test_repr(self):
        td = Td("hello")
        assert repr(td) == "Td: hello"


class TestConstants:
    def test_safe_schemes(self):
        assert "http" in _SAFE_URL_SCHEMES
        assert "https" in _SAFE_URL_SCHEMES
        assert "ftp" not in _SAFE_URL_SCHEMES

    def test_blocked_hosts(self):
        assert "localhost" in _SSRF_BLOCKED_HOSTS
        assert "127.0.0.1" in _SSRF_BLOCKED_HOSTS
        assert "0.0.0.0" in _SSRF_BLOCKED_HOSTS


class TestHtmlModParser:
    def test_init_without_url(self):
        from pytigon_lib.schhtml.htmltools import HtmlModParser

        p = HtmlModParser()
        assert p._tree is None

    def test_init_with_unsafe_url(self):
        from pytigon_lib.schhtml.htmltools import HtmlModParser

        with pytest.raises(ValueError, match="security"):
            HtmlModParser(url="http://localhost:8000")


class TestHtmlProxyParser:
    def test_imports(self):
        from pytigon_lib.schhtml.htmltools import HtmlProxyParser

        assert HtmlProxyParser is not None
