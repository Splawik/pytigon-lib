"""Tests for :mod:`pytigon_lib.schhttptools.httpclient` utility functions and classes."""

import pytest

from pytigon_lib.schhttptools.httpclient import (
    RetHttp,
    decode,
    join_http_path,
    schurljoin,
)


class TestDecode:
    def test_bytes_utf8(self):
        assert decode(b"hello") == "hello"

    def test_string_passes_through(self):
        assert decode("hello") == "hello"

    def test_empty_bytes(self):
        assert decode(b"") == ""

    def test_polish_bytes(self):
        assert decode("Zażółć".encode("utf-8")) == "Zażółć"

    def test_none_passes_through(self):
        result = decode(None)
        assert result is None


class TestSchurljoin:
    def test_basic_join(self):
        result = schurljoin("http://example.com", "/path")
        assert result == "http://example.com/path"

    def test_no_double_slash(self):
        result = schurljoin("http://example.com/", "/path")
        assert result == "http://example.com/path"

    def test_preserve_protocol_slashes(self):
        result = schurljoin("http://example.com/", "/path")
        assert result.count("://") == 1

    def test_empty_address(self):
        result = schurljoin("http://base", "")
        assert result == "http://base"

    def test_base_without_slash_address_with_slash(self):
        result = schurljoin("http://example.com/path", "/extra")
        assert result == "http://example.com/path/extra"


class TestRetHttp:
    def test_basic_response(self):
        message = {
            "body": b"hello",
            "status": 200,
            "headers": {"Content-Type": "text/html"},
            "type": "http.response.body",
        }
        ret = RetHttp("http://test", message)
        assert ret.content == b"hello"
        assert ret.status_code == 200
        assert ret.headers["content-type"] == "text/html"

    def test_set_cookie(self):
        message = {
            "body": b"",
            "status": 200,
            "headers": {"set-cookie": "session=abc123"},
        }
        ret = RetHttp("http://test", message)
        assert "session" in ret.cookies

    def test_status_from_tuple(self):
        message = {"body": b"", "status": (200, "OK")}
        ret = RetHttp("http://test", message)
        assert ret.status_code == 200

    def test_empty_message(self):
        ret = RetHttp("http://test", {})
        assert ret.content == b""
        assert ret.status_code == 200

    def test_cookies_key(self):
        message = {"body": b"", "cookies": {"session": "xyz"}}
        ret = RetHttp("http://test", message)
        assert ret.cookies["session"] == "xyz"

    def test_url_override(self):
        message = {"body": b"", "url": "http://redirected"}
        ret = RetHttp("http://original", message)
        assert ret.url == "http://redirected"

    def test_history_key(self):
        message = {"body": b"", "history": ["url1", "url2"]}
        ret = RetHttp("http://test", message)
        assert ret.history == ["url1", "url2"]


class TestJoinHttpPath:
    def test_slash_on_both(self):
        result = join_http_path("http://base/", "/extra")
        assert result == "http://base/extra"

    def test_no_slash_on_base(self):
        result = join_http_path("http://base", "/extra")
        assert result == "http://base/extra"

    def test_no_slash_on_ext(self):
        result = join_http_path("http://base/", "extra")
        assert result == "http://base/extra"

    def test_neither_has_slash(self):
        result = join_http_path("http://base", "extra")
        assert result == "http://baseextra"
