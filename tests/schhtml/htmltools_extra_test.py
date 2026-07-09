"""Extra tests for :mod:`pytigon_lib.schhtml.htmltools`."""
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schhtml.htmltools import (
    _SAFE_URL_SCHEMES,
    _SSRF_BLOCKED_HOSTS,
    _is_safe_url,
    superstrip,
    Td,
    HtmlModParser,
    HtmlProxyParser,
)


class TestIsSafeUrlExtra:
    def test_ipv4_loopback_blocked(self):
        assert not _is_safe_url("http://127.0.0.1:8000")

    def test_ipv6_loopback_blocked(self):
        assert not _is_safe_url("http://[::1]:8000")

    def test_ipv6_short_blocked(self):
        assert not _is_safe_url("http://[::1]:8080/path")

    def test_private_192_168_0_blocked(self):
        assert not _is_safe_url("http://192.168.0.1")

    def test_private_10_0_blocked(self):
        assert not _is_safe_url("http://10.0.0.1")

    def test_private_172_17_blocked(self):
        assert not _is_safe_url("http://172.17.0.1")

    def test_public_11_allowed(self):
        assert _is_safe_url("http://11.0.0.1")

    def test_https_scheme_allowed(self):
        assert _is_safe_url("https://secure.example.com")

    def test_javascript_scheme_blocked(self):
        assert not _is_safe_url("javascript:alert(1)")

    def test_data_scheme_blocked(self):
        assert not _is_safe_url("data:text/html,<script>alert(1)</script>")

    def test_no_scheme_blocked(self):
        assert not _is_safe_url("example.com")

    def test_gopher_blocked(self):
        assert not _is_safe_url("gopher://example.com")

    def test_https_localhost_blocked(self):
        assert not _is_safe_url("https://localhost:443")


class TestSuperstripExtra:
    def test_carriage_return(self):
        assert superstrip("hello\rworld") == "hello world"

    def test_combined_whitespace(self):
        assert superstrip("  a \n b \r c \t d  ") == "a b c d"

    def test_single_word(self):
        assert superstrip("hello") == "hello"

    def test_only_whitespace(self):
        assert superstrip("   \n\r\t   ") == ""

    def test_16_spaces(self):
        assert superstrip("a" + " " * 16 + "b") == "a b"


class TestTdExtra:
    def test_attr_is_empty_string(self):
        td = Td("data", {"colspan": "2"})
        assert td.attr == ""

    def test_repr_multiline_data(self):
        td = Td("hello\nworld")
        assert "Td:" in repr(td)
        assert "hello" in repr(td)

    def test_children_empty_list(self):
        td = Td("data", children=[])
        assert td.children == []

    def test_all_attrs_preserved(self):
        td = Td("data", {"colspan": "2", "rowspan": "3"})
        assert td.attrs["colspan"] == "2"
        assert td.attrs["rowspan"] == "3"


class TestHtmlModParserExtra:
    def test_init_no_url(self):
        p = HtmlModParser()
        assert p._tree is None

    @patch("pytigon_lib.schhtml.htmltools._is_safe_url", return_value=False)
    def test_unsafe_url_raises(self, mock_safe):
        with pytest.raises(ValueError, match="security"):
            HtmlModParser(url="http://blocked.example.com")

    @patch("pytigon_lib.schhtml.htmltools.urlopen")
    def test_valid_url_fetches(self, mock_urlopen):
        mock_urlopen.return_value.read.return_value = b"<html></html>"
        with patch("pytigon_lib.schhtml.htmltools._is_safe_url", return_value=True):
            p = HtmlModParser(url="http://safe.example.com")
            assert p._tree is not None


class TestHtmlProxyParserExtra:
    def test_class_exists(self):
        assert HtmlProxyParser is not None

    def test_imports_work(self):
        from pytigon_lib.schhtml.htmltools import HtmlProxyParser as HPP
        assert HPP is not None
