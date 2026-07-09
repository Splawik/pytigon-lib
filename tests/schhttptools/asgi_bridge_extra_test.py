"""Extra tests for :mod:`pytigon_lib.schhttptools.asgi_bridge`."""
from unittest.mock import AsyncMock, MagicMock

import pytest

from pytigon_lib.schhttptools.asgi_bridge import (
    SCOPE_TEMPLATE,
    get_or_post,
    get_scope_and_content_http_get,
    get_scope_and_content_http_post,
    get_scope_websocket,
    websocket,
)


class TestScopeTemplate:
    def test_template_has_required_keys(self):
        assert "type" in SCOPE_TEMPLATE
        assert "method" in SCOPE_TEMPLATE
        assert "path" in SCOPE_TEMPLATE
        assert "headers" in SCOPE_TEMPLATE
        assert "client" in SCOPE_TEMPLATE
        assert "server" in SCOPE_TEMPLATE

    def test_template_headers_are_bytes(self):
        for key, value in SCOPE_TEMPLATE["headers"]:
            assert isinstance(key, bytes)
            assert isinstance(value, bytes)


class TestGetScopeAndContentHttpGet:
    def test_simple_path(self):
        scope, content = get_scope_and_content_http_get("/test", [])
        assert scope["path"] == "/test"
        assert content == ""

    def test_path_with_query_string(self):
        scope, content = get_scope_and_content_http_get("/test?a=1&b=2", [])
        assert scope["path"] == "/test"
        assert scope["query_string"] == b"a=1&b=2"

    def test_custom_headers(self):
        headers = [("X-Custom", "value"), ("Authorization", "Bearer token")]
        scope, content = get_scope_and_content_http_get("/api", headers)
        headers_lower = {k.lower(): v for k, v in scope["headers"]}
        assert b"x-custom" in headers_lower
        assert b"authorization" in headers_lower

    def test_header_casing_normalized(self):
        headers = [("CONTENT-TYPE", "text/html")]
        scope, _ = get_scope_and_content_http_get("/", headers)
        headers_lower = {k.lower(): v for k, v in scope["headers"]}
        assert b"content-type" in headers_lower

    def test_path_without_query(self):
        scope, _ = get_scope_and_content_http_get("/path", [])
        assert scope["query_string"] == b""

    def test_empty_headers(self):
        scope, content = get_scope_and_content_http_get("/", [])
        assert isinstance(scope["headers"], list)

    def test_scope_is_copy_not_reference(self):
        scope1, _ = get_scope_and_content_http_get("/one", [])
        scope2, _ = get_scope_and_content_http_get("/two", [])
        assert scope1["path"] != scope2["path"]


class TestGetScopeAndContentHttpPost:
    def test_sets_post_method(self):
        scope, content = get_scope_and_content_http_post("/submit", [], {})
        assert scope["method"] == "POST"

    def test_with_params(self):
        scope, content = get_scope_and_content_http_post(
            "/submit", [], {"key": "value", "x": "y"}
        )
        assert "key=value" in content
        assert "x=y" in content

    def test_without_params(self):
        scope, content = get_scope_and_content_http_post("/submit", [], None)
        assert content == ""

    def test_content_length_header(self):
        scope, content = get_scope_and_content_http_post(
            "/submit", [], {"a": "b"}
        )
        content_length_header = next(
            (v for k, v in scope["headers"] if k == b"content-length"),
            None,
        )
        assert content_length_header is not None
        assert content_length_header == str(len(content)).encode("utf-8")

    def test_content_type_header(self):
        scope, _ = get_scope_and_content_http_post("/submit", [], {})
        assert (b"content-type", b"application/x-www-form-urlencoded") in scope["headers"]

    def test_headers_preserved_from_get(self):
        headers = [("X-Test", "yes")]
        scope, _ = get_scope_and_content_http_post("/submit", headers, {})
        headers_lower = {k.lower(): v for k, v in scope["headers"]}
        assert b"x-test" in headers_lower


class TestGetScopeWebSocket:
    def test_sets_websocket_type(self):
        scope = get_scope_websocket("/ws", [])
        assert scope["type"] == "websocket"

    def test_path_preserved(self):
        scope = get_scope_websocket("/ws/test", [])
        assert scope["path"] == "/ws/test"

    def test_headers_preserved(self):
        headers = [("X-WS", "val")]
        scope = get_scope_websocket("/ws", headers)
        headers_lower = {k.lower(): v for k, v in scope["headers"]}
        assert b"x-ws" in headers_lower


class TestGetOrPostExtra:
    @pytest.mark.asyncio
    async def test_get_request(self):
        app = AsyncMock()
        response = await get_or_post(app, "/test", [])
        assert isinstance(response, dict)

    @pytest.mark.asyncio
    async def test_post_request(self):
        app = AsyncMock()
        response = await get_or_post(
            app, "/submit", [("Content-Type", "text/html")], {"x": "1"}, post=True
        )
        assert isinstance(response, dict)


class TestWebSocketExtra:
    @pytest.mark.asyncio
    async def test_websocket_basic(self):
        app = AsyncMock()
        output = MagicMock()
        input_queue = AsyncMock()
        response = await websocket(app, "ws://127.0.0.2/test", [], input_queue, output)
        assert isinstance(response, dict)
