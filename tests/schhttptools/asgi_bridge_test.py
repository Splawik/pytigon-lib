from pytigon_lib.schhttptools.asgi_bridge import *

# Pytest tests
import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_get_scope_and_content_http_get():
    headers = [("X-Test-Header", "test-value")]
    scope, content = get_scope_and_content_http_get("/test", headers)
    assert scope["path"] == "/test"
    assert (b"x-test-header", b"test-value") in scope["headers"]


@pytest.mark.asyncio
async def test_get_scope_and_content_http_post():
    headers = [("X-Test-Header", "test-value")]
    params = {"key": "value"}
    scope, content = get_scope_and_content_http_post("/test", headers, params)
    assert scope["method"] == "POST"
    assert content == "key=value"


@pytest.mark.asyncio
async def test_get_or_post():
    mock_app = AsyncMock()
    headers = [("X-Test-Header", "test-value")]
    response = await get_or_post(mock_app, "/test", headers)
    assert isinstance(response, dict)


@pytest.mark.asyncio
async def test_websocket():
    mock_app = AsyncMock()
    mock_output = MagicMock()
    headers = [("X-Test-Header", "test-value")]
    input_queue = AsyncMock()
    response = await websocket(
        mock_app, "ws://127.0.0.2/test", headers, input_queue, mock_output
    )
    assert isinstance(response, dict)
