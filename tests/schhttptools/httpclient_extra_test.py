"""Extra tests for :mod:`pytigon_lib.schhttptools.httpclient` — uncovered functions and classes."""

import base64
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

from pytigon_lib.schhttptools.httpclient import (
    AppHttp,
    HttpClient,
    HttpResponse,
    RetHttp,
    decode,
    init_embeded_django,
    join_http_path,
    local_websocket,
    request,
    set_http_error_func,
    set_http_idle_func,
)


def _configure_django():
    from django.conf import settings

    if not settings.configured:
        settings.configure(
            ALLOWED_HOSTS=[],
            SECRET_KEY="test",
            ROOT_URLCONF="django.urls",
            STATIC_URL="/static/",
            DATA_PATH="/tmp",
            INSTALLED_APPS=[],
        )


class TestInitEmbededDjango:
    def test_emscripten_path(self):
        _configure_django()
        import pytigon_lib.schhttptools.httpclient as mod

        with (
            patch("pytigon_lib.schhttptools.httpclient.platform_name", return_value="Emscripten"),
            patch("django.setup") as mock_dj_setup,
            patch("pytigon_lib.schhttptools.httpclient.get_wsgi_application", return_value="wsgi_app"),
        ):
            mod.ASGI_APPLICATION = None
            init_embeded_django()
            mock_dj_setup.assert_called_once()
            assert mod.ASGI_APPLICATION == "wsgi_app"

    def test_force_wsgi_path(self):
        _configure_django()
        import pytigon_lib.schhttptools.httpclient as mod

        with (
            patch("pytigon_lib.schhttptools.httpclient.platform_name", return_value="Linux"),
            patch("django.setup") as mock_dj_setup,
            patch("pytigon_lib.schhttptools.httpclient.get_wsgi_application", return_value="wsgi_app"),
        ):
            old_force = mod.FORCE_WSGI
            mod.FORCE_WSGI = True
            mod.ASGI_APPLICATION = None
            try:
                init_embeded_django()
                assert mod.ASGI_APPLICATION == "wsgi_app"
                mock_dj_setup.assert_called_once()
            finally:
                mod.FORCE_WSGI = old_force
                mod.ASGI_APPLICATION = None

    def test_channels_path(self):
        _configure_django()
        import pytigon_lib.schhttptools.httpclient as mod

        with (
            patch("pytigon_lib.schhttptools.httpclient.platform_name", return_value="Linux"),
            patch("django.setup") as mock_dj_setup,
            patch(
                "channels.routing.get_default_application",
                return_value="channels_app",
            ) as mock_channels,
        ):
            old_force = mod.FORCE_WSGI
            mod.FORCE_WSGI = False
            mod.ASGI_APPLICATION = None
            try:
                init_embeded_django()
                assert mod.ASGI_APPLICATION == "channels_app"
                mock_channels.assert_called_once()
                mock_dj_setup.assert_called_once()
            finally:
                mod.ASGI_APPLICATION = None
                mod.FORCE_WSGI = old_force

    def test_appends_allowed_hosts(self):
        _configure_django()
        from django.conf import settings

        old_allowed = list(settings.ALLOWED_HOSTS)
        try:
            with (
                patch("pytigon_lib.schhttptools.httpclient.platform_name", return_value="Emscripten"),
                patch("django.setup"),
                patch("pytigon_lib.schhttptools.httpclient.get_wsgi_application", return_value="wsgi_app"),
            ):
                if "testserver" not in settings.ALLOWED_HOSTS:
                    init_embeded_django()
                    assert "testserver" in settings.ALLOWED_HOSTS
        finally:
            settings.ALLOWED_HOSTS[:] = old_allowed


class TestSetHttpErrorFunc:
    def test_sets_global(self):
        import pytigon_lib.schhttptools.httpclient as mod

        def fake_func(parent, content):
            pass

        old = mod.HTTP_ERROR_FUNC
        try:
            set_http_error_func(fake_func)
            assert mod.HTTP_ERROR_FUNC is fake_func
        finally:
            mod.HTTP_ERROR_FUNC = old

    def test_overwrites_previous(self):
        import pytigon_lib.schhttptools.httpclient as mod

        def a(parent, content):
            pass

        def b(parent, content):
            pass

        old = mod.HTTP_ERROR_FUNC
        try:
            set_http_error_func(a)
            set_http_error_func(b)
            assert mod.HTTP_ERROR_FUNC is b
        finally:
            mod.HTTP_ERROR_FUNC = old


class TestSetHttpIdleFunc:
    def test_sets_global(self):
        import pytigon_lib.schhttptools.httpclient as mod

        def fake_func():
            pass

        old = mod.HTTP_IDLE_FUNC
        try:
            set_http_idle_func(fake_func)
            assert mod.HTTP_IDLE_FUNC is fake_func
        finally:
            mod.HTTP_IDLE_FUNC = old

    def test_can_be_none(self):
        import pytigon_lib.schhttptools.httpclient as mod

        old = mod.HTTP_IDLE_FUNC
        try:
            set_http_idle_func(None)
            assert mod.HTTP_IDLE_FUNC is None
        finally:
            mod.HTTP_IDLE_FUNC = old


class TestHttpClientConstructor:
    def test_default_address(self):
        client = HttpClient()
        assert client.base_address == "http://127.0.0.2"

    def test_custom_address(self):
        client = HttpClient("http://example.com")
        assert client.base_address == "http://example.com"

    def test_cache_initialised_empty(self):
        client = HttpClient()
        assert client.http_cache == {}

    def test_app_is_none_by_default(self):
        client = HttpClient()
        assert client.app is None


class TestHttpClientClose:
    def test_close_does_not_raise(self):
        client = HttpClient()
        client.close()


class TestHttpClientShow:
    def test_show_with_error_func_set(self):
        import pytigon_lib.schhttptools.httpclient as mod

        called_with = []

        def fake_error(parent, content):
            called_with.append((parent, content))

        old = mod.HTTP_ERROR_FUNC
        try:
            mod.HTTP_ERROR_FUNC = fake_error
            client = HttpClient()
            client.content = b"test error content"
            client.show("parent_obj")
            assert len(called_with) == 1
            assert called_with[0][0] == "parent_obj"
            assert called_with[0][1] == b"test error content"
        finally:
            mod.HTTP_ERROR_FUNC = old

    def test_show_without_error_func(self):
        import pytigon_lib.schhttptools.httpclient as mod

        old = mod.HTTP_ERROR_FUNC
        try:
            mod.HTTP_ERROR_FUNC = None
            client = HttpClient()
            client.show("parent_obj")
        finally:
            mod.HTTP_ERROR_FUNC = old


class TestAppHttpConstructor:
    def test_stores_app(self):
        app = MagicMock()
        client = AppHttp("http://base", app)
        assert client.app is app
        assert client.base_address == "http://base"

    def test_inherits_from_httpclient(self):
        app = MagicMock()
        client = AppHttp("http://base", app)
        assert isinstance(client, HttpClient)

    def test_default_address_when_empty(self):
        app = MagicMock()
        client = AppHttp("", app)
        assert client.base_address == "http://127.0.0.2"


class TestHttpClientGetDataUri:
    def test_get_data_uri_base64(self):
        data = base64.b64encode(b"hello world").decode("utf-8")
        uri = f"data:text/plain;base64,{data}"
        client = HttpClient()
        result = client.get(None, uri)
        assert isinstance(result, HttpResponse)
        assert result.content == b"hello world"
        assert result.ret_content_type == "text/plain"
        assert result.ret_code == 200

    def test_get_data_uri_invalid(self):
        client = HttpClient()
        result = client.get(None, "data:badformat")
        assert isinstance(result, HttpResponse)
        assert result.ret_code == 500

    def test_get_data_uri_no_semicolons_crashes(self):
        client = HttpClient()
        with pytest.raises(IndexError):
            client.get(None, "data:text/plain,rawtext")


class TestHttpClientGetCache:
    @patch("pytigon_lib.schhttptools.httpclient.request")
    def test_get_cache_skipped_for_post(self, mock_req):
        mock_req.return_value = MagicMock(
            status_code=200, content=b"new", headers={},
            cookies=MagicMock(items=lambda: []), history=None, url="http://127.0.0.2/test"
        )
        client = HttpClient()
        client.http_cache["http://127.0.0.2/test"] = ("text/html", b"old")
        result = client.get(None, "http://127.0.0.2/test", post_request=True)
        assert result.content == b"new"

    @patch("pytigon_lib.schhttptools.httpclient.request")
    def test_get_cache_used_for_get(self, mock_req):
        client = HttpClient()
        client.http_cache["http://127.0.0.2/cached"] = ("text/html", b"cached content")
        result = client.get(None, "http://127.0.0.2/cached")
        assert isinstance(result, HttpResponse)
        assert result.content == b"cached content"
        assert result.ret_content_type == "text/html"
        mock_req.assert_not_called()

    @patch("pytigon_lib.schhttptools.httpclient.request")
    def test_get_cache_skipped_when_query_string_present(self, mock_req):
        mock_req.return_value = MagicMock(
            status_code=200, content=b"fresh", headers={},
            cookies=MagicMock(items=lambda: []), history=None, url="http://127.0.0.2/path?a=1"
        )
        client = HttpClient()
        client.http_cache["http://127.0.0.2/path?a=1"] = ("text/html", b"old")
        result = client.get(None, "http://127.0.0.2/path?a=1")
        assert result.content == b"fresh"

    @patch("pytigon_lib.schhttptools.httpclient.request")
    def test_carat_prefix_rewrites_address(self, mock_req):
        mock_req.return_value = MagicMock(
            status_code=200, content=b"", headers={},
            cookies=MagicMock(items=lambda: []), history=None, url="http://127.0.0.2/plugins/plugin_route"
        )
        client = HttpClient()
        client.get(None, "^plugin_route")
        call_args = mock_req.call_args
        assert call_args is not None
        rewritten = call_args[0][1]
        assert rewritten.startswith("http://127.0.0.2/plugins/plugin_route")


class TestHttpClientGetPostIntegration:
    @patch("pytigon_lib.schhttptools.httpclient.request")
    def test_get_with_request_mock(self, mock_req):
        mock_req.return_value = MagicMock(
            status_code=200, content=b"resp", headers={"content-type": "text/html"},
            cookies=MagicMock(items=lambda: []), history=None, url="http://127.0.0.2/test"
        )
        client = HttpClient()
        result = client.get(None, "http://127.0.0.2/test")
        assert isinstance(result, HttpResponse)
        assert result.content == b"resp"

    @patch("pytigon_lib.schhttptools.httpclient.request")
    def test_post_calls_get_with_post_request_flag(self, mock_req):
        mock_req.return_value = MagicMock(
            status_code=200, content=b"post_resp", headers={"content-type": "application/json"},
            cookies=MagicMock(items=lambda: []), history=None, url="http://127.0.0.2/submit"
        )
        client = HttpClient()
        result = client.post(None, "http://127.0.0.2/submit")
        assert result.content == b"post_resp"

    @patch("pytigon_lib.schhttptools.httpclient.request")
    def test_post_with_json_data(self, mock_req):
        mock_req.return_value = MagicMock(
            status_code=200, content=b"json_resp", headers={"content-type": "application/json"},
            cookies=MagicMock(items=lambda: []), history=None, url="http://127.0.0.2/api"
        )
        client = HttpClient()
        result = client.get(None, "http://127.0.0.2/api", parm={"key": "val"}, post_request=True, json_data=True)
        assert result.content == b"json_resp"

    @patch("pytigon_lib.schhttptools.httpclient.request")
    def test_post_with_csrf_token(self, mock_req):
        import pytigon_lib.schhttptools.httpclient as mod

        mock_req.return_value = MagicMock(
            status_code=200, content=b"ok", headers={},
            cookies=MagicMock(items=lambda: []), history=None, url="http://127.0.0.2/submit"
        )
        old = dict(mod.COOKIES_EMBEDED)
        try:
            mod.COOKIES_EMBEDED["csrftoken"] = "abc123"
            client = HttpClient()
            client.get(None, "http://127.0.0.2/submit", parm={"x": "1"}, post_request=True)
            call_args = mock_req.call_args
            assert call_args is not None
            argv = call_args[0][3]
            assert "X-CSRFToken" in argv["headers"]
            assert argv["headers"]["X-CSRFToken"] == "abc123"
        finally:
            mod.COOKIES_EMBEDED.clear()
            mod.COOKIES_EMBEDED.update(old)

    @patch("pytigon_lib.schhttptools.httpclient.request")
    def test_get_passes_user_agent(self, mock_req):
        mock_req.return_value = MagicMock(
            status_code=200, content=b"", headers={},
            cookies=MagicMock(items=lambda: []), history=None, url="http://127.0.0.2/test"
        )
        client = HttpClient()
        client.get(None, "http://127.0.0.2/test", user_agent="custom_agent")
        call_args = mock_req.call_args
        assert call_args is not None
        assert call_args[0][3]["headers"]["User-Agent"] == "custom_agent"

    @patch("pytigon_lib.schhttptools.httpclient.request")
    def test_get_with_credentials(self, mock_req):
        mock_req.return_value = MagicMock(
            status_code=200, content=b"", headers={},
            cookies=MagicMock(items=lambda: []), history=None, url="http://127.0.0.2/test"
        )
        client = HttpClient()
        client.get(None, "http://127.0.0.2/test", credentials=("user", "pass"))
        call_args = mock_req.call_args
        assert call_args is not None
        assert call_args[0][3]["auth"] == ("user", "pass")


class TestHttpClientFileUrl:
    @patch("pytigon_lib.schhttptools.httpclient.open_file")
    @patch("mimetypes.types_map", {".txt": "text/plain"})
    def test_file_url_read(self, mock_open_file):
        mock_open_file.return_value.__enter__.return_value.read.return_value = b"file content"
        mock_open_file.return_value.__exit__ = MagicMock(return_value=False)
        client = HttpClient()
        result = client.get(None, "file:///tmp/test.txt")
        assert result.content == b"file content"
        assert result.ret_content_type == "text/plain"

    @patch("pytigon_lib.schhttptools.httpclient.open_file")
    @patch("mimetypes.types_map", {".txt": "text/plain"})
    def test_file_url_windows_style_path(self, mock_open_file):
        mock_open_file.return_value.__enter__.return_value.read.return_value = b"win"
        mock_open_file.return_value.__exit__ = MagicMock(return_value=False)
        client = HttpClient()
        result = client.get(None, "file:///C:/test.txt")
        assert result.content == b"win"


class TestHttpClientBlockLoop:
    @patch("pytigon_lib.schhttptools.httpclient.request")
    def test_block_loop_bails_when_exception_in_idle(self, mock_req):
        import pytigon_lib.schhttptools.httpclient as mod

        old_block = mod.BLOCK
        old_idle = mod.HTTP_IDLE_FUNC

        def bad_idle():
            raise RuntimeError("idle failure")

        try:
            mod.BLOCK = True
            mod.HTTP_IDLE_FUNC = bad_idle
            mock_req.return_value = MagicMock(
                status_code=200, content=b"", headers={},
                cookies=MagicMock(items=lambda: []), history=None, url="http://127.0.0.2/test"
            )
            client = HttpClient()
            result = client.get(None, "http://127.0.0.2/test")
            assert result.ret_code == 500
        finally:
            mod.BLOCK = old_block
            mod.HTTP_IDLE_FUNC = old_idle

    @patch("pytigon_lib.schhttptools.httpclient.request")
    def test_block_idle_func_called(self, mock_req):
        import pytigon_lib.schhttptools.httpclient as mod

        old_block = mod.BLOCK
        old_idle = mod.HTTP_IDLE_FUNC
        idle_calls = []

        def idle():
            idle_calls.append(1)
            mod.BLOCK = False

        try:
            mod.BLOCK = True
            mod.HTTP_IDLE_FUNC = idle
            mock_req.return_value = MagicMock(
                status_code=200, content=b"ok", headers={},
                cookies=MagicMock(items=lambda: []), history=None, url="http://127.0.0.2/test"
            )
            client = HttpClient()
            result = client.get(None, "http://127.0.0.2/test")
            assert result.content == b"ok"
            assert len(idle_calls) >= 1
        finally:
            mod.BLOCK = old_block
            mod.HTTP_IDLE_FUNC = old_idle


class TestHttpResponseProcessResponse:
    def test_sets_content_and_code(self):
        http_client = MagicMock()
        http_client.http_cache = MagicMock()
        mock_response = MagicMock()
        mock_response.content = b"body"
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.cookies = MagicMock(items=lambda: [])
        mock_response.history = None
        mock_response.url = "http://example.com/test"

        hr = HttpResponse("http://example.com/test")
        hr.response = mock_response
        hr.process_response(http_client, None, False)
        assert hr.content == b"body"
        assert hr.ret_code == 200

    def test_caches_non_post_questionless_url(self):
        class MockClient:
            http_cache = {}

        http_client = MockClient()
        mock_response = MagicMock()
        mock_response.content = b"Cache-control: max-age=3600\ncached"
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "text/html"}
        mock_response.cookies = MagicMock(items=lambda: [])
        mock_response.history = None
        mock_response.url = "http://example.com/test"

        hr = HttpResponse("http://example.com/test")
        hr.response = mock_response
        hr.process_response(http_client, None, False)
        expected = ("text/html", b"Cache-control: max-age=3600\ncached")
        assert "http://example.com/test" in http_client.http_cache
        assert http_client.http_cache["http://example.com/test"] == expected

    def test_logs_error_on_non_200(self):
        http_client = MagicMock()
        http_client.http_cache = MagicMock()
        mock_response = MagicMock()
        mock_response.content = b"error"
        mock_response.status_code = 500
        mock_response.headers = {}
        mock_response.cookies = MagicMock(items=lambda: [])
        mock_response.history = None
        mock_response.url = "http://example.com/test"

        hr = HttpResponse("http://example.com/test")
        hr.response = mock_response
        with patch("pytigon_lib.schhttptools.httpclient.LOGGER") as mock_logger:
            hr.process_response(http_client, None, False)
            mock_logger.error.assert_called()

    def test_propagates_cookies_from_history(self):
        import pytigon_lib.schhttptools.httpclient as mod

        http_client = MagicMock()
        http_client.http_cache = MagicMock()
        hist_entry = MagicMock()
        hist_entry.cookies = MagicMock()
        hist_entry.cookies.items.return_value = [("session", "abc")]
        mock_response = MagicMock()
        mock_response.content = b""
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.cookies = MagicMock(items=lambda: [])
        mock_response.history = [hist_entry]
        mock_response.url = "http://127.0.0.2/test"

        old_cookies = dict(mod.COOKIES_EMBEDED)
        try:
            hr = HttpResponse("http://127.0.0.2/test")
            hr.response = mock_response
            hr.process_response(http_client, None, False)
            assert mod.COOKIES_EMBEDED.get("session") == "abc"
        finally:
            mod.COOKIES_EMBEDED.clear()
            mod.COOKIES_EMBEDED.update(old_cookies)

    def test_propagates_response_cookies(self):
        import pytigon_lib.schhttptools.httpclient as mod

        http_client = MagicMock()
        http_client.http_cache = MagicMock()
        mock_response = MagicMock()
        mock_response.content = b""
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.cookies = MagicMock()
        mock_response.cookies.items.return_value = [("token", "xyz")]
        mock_response.history = None
        mock_response.url = "http://127.0.0.2/test"

        old_cookies = dict(mod.COOKIES_EMBEDED)
        try:
            hr = HttpResponse("http://127.0.0.2/test")
            hr.response = mock_response
            hr.process_response(http_client, None, False)
            assert mod.COOKIES_EMBEDED.get("token") == "xyz"
        finally:
            mod.COOKIES_EMBEDED.clear()
            mod.COOKIES_EMBEDED.update(old_cookies)

    def test_traceback_in_content_triggers_error_func(self):
        import pytigon_lib.schhttptools.httpclient as mod

        old_err = mod.HTTP_ERROR_FUNC
        called = []

        def fake_error(parent, content):
            called.append((parent, content))

        mod.HTTP_ERROR_FUNC = fake_error
        try:
            http_client = MagicMock()
            http_client.http_cache = MagicMock()
            mock_response = MagicMock()
            mock_response.content = b"Traceback (most recent call last): ... copy-and-paste ..."
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/html"}
            mock_response.cookies = MagicMock(items=lambda: [])
            mock_response.history = None
            mock_response.url = "http://example.com/test"

            hr = HttpResponse("http://example.com/test")
            hr.response = mock_response
            hr.process_response(http_client, "parent_obj", False)
            assert len(called) == 1
            assert hr.ret_content_type == "500"
            assert hr.content == b""
        finally:
            mod.HTTP_ERROR_FUNC = old_err

    def test_traceback_writes_to_file_when_no_error_func(self):
        _configure_django()
        import pytigon_lib.schhttptools.httpclient as mod

        old_err = mod.HTTP_ERROR_FUNC
        mod.HTTP_ERROR_FUNC = None
        try:
            http_client = MagicMock()
            http_client.http_cache = MagicMock()
            mock_response = MagicMock()
            mock_response.content = b"Traceback ... copy-and-paste the above"
            mock_response.status_code = 200
            mock_response.headers = {"content-type": "text/html"}
            mock_response.cookies = MagicMock(items=lambda: [])
            mock_response.history = None
            mock_response.url = "http://example.com/test"

            hr = HttpResponse("http://example.com/test")
            hr.response = mock_response
            with patch("builtins.open", mock_open()):
                hr.process_response(http_client, "parent_obj", False)
            assert hr.ret_content_type == "500"
            assert hr.content == b""
        finally:
            mod.HTTP_ERROR_FUNC = old_err

    def test_sets_new_url_from_response(self):
        http_client = MagicMock()
        http_client.http_cache = MagicMock()
        mock_response = MagicMock()
        mock_response.content = b""
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.cookies = MagicMock(items=lambda: [])
        mock_response.history = None
        mock_response.url = "http://final/url"

        hr = HttpResponse("http://initial/url")
        hr.response = mock_response
        hr.process_response(http_client, None, False)
        assert hr.new_url == "http://final/url"


class TestHttpResponseStrJsonPtr:
    def test_str_text_content(self):
        hr = HttpResponse("http://test")
        hr.ret_content_type = "text/plain"
        hr.content = b"hello world"
        assert hr.str() == "hello world"

    def test_str_non_text_content(self):
        hr = HttpResponse("http://test")
        hr.ret_content_type = "application/octet-stream"
        hr.content = b"\x00\x01"
        result = hr.str()
        assert result == b"\x00\x01"

    def test_json(self):
        hr = HttpResponse("http://test")
        hr.ret_content_type = "text/json"
        hr.content = b'{"key": "value"}'
        assert hr.json() == {"key": "value"}

    def test_to_python(self):
        hr = HttpResponse("http://test")
        hr.ret_content_type = "text/json"
        hr.content = b'[1, 2, 3]'
        assert hr.to_python() == [1, 2, 3]

    def test_ptr(self):
        hr = HttpResponse("http://test")
        hr.content = b"raw"
        assert hr.ptr() == b"raw"

    def test_str_iso_8859_2(self):
        hr = HttpResponse("http://test")
        hr.ret_content_type = "text/html; charset=iso-8859-2"
        hr.content = b"\xa3"
        assert hr.str() == "\u0141"


class TestLocalWebSocket:
    @pytest.mark.asyncio
    async def test_basic_call(self):
        import pytigon_lib.schhttptools.httpclient as mod

        with (
            patch.dict(mod.COOKIES_EMBEDED, {"session": "abc", "csrftoken": "tok"}),
            patch("pytigon_lib.schhttptools.httpclient.websocket", new_callable=AsyncMock) as mock_ws,
        ):
            mock_ws.return_value = {"result": "ok"}
            input_queue = AsyncMock()
            output = MagicMock()
            old_asgi = mod.ASGI_APPLICATION
            try:
                mod.ASGI_APPLICATION = MagicMock()
                result = await local_websocket("/test/ws", input_queue, output)
                assert result == {"result": "ok"}
                assert mock_ws.called
            finally:
                mod.ASGI_APPLICATION = old_asgi

    @pytest.mark.asyncio
    async def test_without_csrf_token(self):
        import pytigon_lib.schhttptools.httpclient as mod

        old_cookies = dict(mod.COOKIES_EMBEDED)
        try:
            mod.COOKIES_EMBEDED.clear()
            with patch("pytigon_lib.schhttptools.httpclient.websocket", new_callable=AsyncMock) as mock_ws:
                mock_ws.return_value = {}
                input_queue = AsyncMock()
                output = MagicMock()
                old_asgi = mod.ASGI_APPLICATION
                try:
                    mod.ASGI_APPLICATION = MagicMock()
                    result = await local_websocket("/ws", input_queue, output)
                    assert result == {}
                finally:
                    mod.ASGI_APPLICATION = old_asgi
        finally:
            mod.COOKIES_EMBEDED.update(old_cookies)


class TestRequestModuleFunction:
    def test_direct_post_emscripten(self):
        import pytigon_lib.schhttptools.httpclient as mod

        with (
            patch("pytigon_lib.schhttptools.httpclient.platform_name", return_value="Emscripten"),
            patch("pytigon_lib.schhttptools.httpclient.asgi_or_wsgi_get_or_post") as mock_asgi,
        ):
            def side_effect(*args, **kw):
                kwargs = args[5] if len(args) > 5 else kw.get("ret", [])
                kwargs.append({"body": b"ok", "headers": {}, "status": 200, "type": "http.response.body"})

            mock_asgi.side_effect = side_effect
            old_asgi = mod.ASGI_APPLICATION
            try:
                mod.ASGI_APPLICATION = "test_app"
                ret = request("post", "http://127.0.0.2/api", True, {"headers": {}, "data": {}})
                assert isinstance(ret, RetHttp)
                assert ret.content == b"ok"
            finally:
                mod.ASGI_APPLICATION = old_asgi

    def test_direct_get_threaded(self):
        import pytigon_lib.schhttptools.httpclient as mod

        with (
            patch("pytigon_lib.schhttptools.httpclient.platform_name", return_value="Linux"),
            patch("pytigon_lib.schhttptools.httpclient.asgi_or_wsgi_get_or_post") as mock_asgi,
        ):
            def side_effect(*args, **kw):
                kwargs = args[5] if len(args) > 5 else kw.get("ret", [])
                kwargs.append({"body": b"ok", "headers": {}, "status": 200, "type": "http.response.body"})

            mock_asgi.side_effect = side_effect
            old_asgi = mod.ASGI_APPLICATION
            try:
                mod.ASGI_APPLICATION = "test_app"
                ret = request("get", "http://127.0.0.2/api", True, {"headers": {}})
                assert isinstance(ret, RetHttp)
                assert ret.content == b"ok"
            finally:
                mod.ASGI_APPLICATION = old_asgi

    def test_httpx_path(self):
        def side_effect(method, url, argv, ret=None):
            if ret is not None:
                m = MagicMock()
                m.status_code = 200
                m.content = b"httpx_content"
                ret.append(m)

        with patch("pytigon_lib.schhttptools.httpclient.requests_request", side_effect=side_effect):
            ret = request("get", "http://external.com/api", False, {"headers": {}})
            assert ret.status_code == 200
            assert ret.content == b"httpx_content"

    def test_httpx_with_app_yield(self):
        def side_effect(method, url, argv, ret=None):
            if ret is not None:
                m = MagicMock()
                m.status_code = 200
                ret.append(m)

        with patch("pytigon_lib.schhttptools.httpclient.requests_request", side_effect=side_effect):
            app = MagicMock()
            ret = request("get", "http://external.com/api", False, {"headers": {}}, app=app)
            assert ret.status_code == 200


class TestJoinHttpPathExtra:
    def test_empty_base(self):
        result = join_http_path("", "/extra")
        assert result == "/extra"


class TestDecodeEdgeCases:
    def test_int_passes_through(self):
        result = decode(42)
        assert result == 42

    def test_float_passes_through(self):
        result = decode(1.5)
        assert result == 1.5
