from unittest.mock import MagicMock, patch

import pytest
from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory

from pytigon_lib.schviews.actions import (
    _DELETE_ROW_OK_HTML,
    _ERROR_HTML_TEMPLATE,
    _NEW_ROW_OK_HTML,
    _UPDATE_ROW_OK_HTML,
    _build_row_response,
    _is_python_agent,
    delete_row_ok,
    error,
    new_row_ok,
    reload,
    update_row_ok,
)


@pytest.fixture
def rf():
    return RequestFactory()


class TestIsPythonAgent:
    def test_py_user_agent(self, rf):
        request = rf.get("/", HTTP_USER_AGENT="Python/3.12 aiohttp")
        assert _is_python_agent(request) is True

    def test_pytigon_user_agent(self, rf):
        request = rf.get("/", HTTP_USER_AGENT="PyTigon/1.0")
        assert _is_python_agent(request) is True

    def test_browser_user_agent(self, rf):
        request = rf.get("/", HTTP_USER_AGENT="Mozilla/5.0")
        assert _is_python_agent(request) is False

    def test_empty_user_agent(self, rf):
        request = rf.get("/")
        assert _is_python_agent(request) is False

    def test_uppercase_py_agent(self, rf):
        request = rf.get("/", HTTP_USER_AGENT="PYTHON_CLIENT")
        assert _is_python_agent(request) is True


class TestBuildRowResponse:
    def test_non_python_agent_returns_html(self, rf):
        request = rf.get("/", HTTP_USER_AGENT="Mozilla/5.0")
        with patch("pytigon_lib.schviews.actions.model_to_dict") as mock_mtd:
            mock_mtd.return_value = {"id": 1, "name": "test"}
            mock_obj = MagicMock()
            resp = _build_row_response(request, 42, mock_obj, "test_action", _NEW_ROW_OK_HTML)
            assert isinstance(resp, HttpResponse)
            assert b"42" in resp.content
            assert resp.status_code == 200

    def test_python_agent_returns_json(self, rf):
        request = rf.get("/", HTTP_USER_AGENT="python/3.12")
        with patch("pytigon_lib.schviews.actions.model_to_dict") as mock_mtd:
            mock_mtd.return_value = {"id": 7, "name": "test"}
            mock_obj = MagicMock()
            resp = _build_row_response(request, 7, mock_obj, "new", _NEW_ROW_OK_HTML)
            assert isinstance(resp, JsonResponse)


class TestNewRowOk:
    def test_response_contains_meta_tag(self, rf):
        request = rf.get("/")
        mock_obj = MagicMock()
        resp = new_row_ok(request, 99, mock_obj)
        assert b"$$RETURN_NEW_ROW_OK" in resp.content
        assert b"99" in resp.content

    def test_response_status_200(self, rf):
        request = rf.get("/")
        mock_obj = MagicMock()
        resp = new_row_ok(request, 1, mock_obj)
        assert resp.status_code == 200


class TestUpdateRowOk:
    def test_response_contains_meta_tag(self, rf):
        request = rf.get("/")
        mock_obj = MagicMock()
        resp = update_row_ok(request, 5, mock_obj)
        assert b"$$RETURN_UPDATE_ROW_OK" in resp.content
        assert b"5" in resp.content


class TestDeleteRowOk:
    def test_response_contains_meta_tag(self, rf):
        request = rf.get("/")
        mock_obj = MagicMock()
        resp = delete_row_ok(request, 3, mock_obj)
        assert b"$$RETURN_OK" in resp.content
        assert b"3" in resp.content


class TestReload:
    def test_reload_embeds_html_body(self, rf):
        request = rf.get("/")
        resp = reload(request, "<p>new</p>")
        assert b"$$RETURN_RELOAD" in resp.content
        assert b"<p>new</p>" in resp.content


class TestError:
    def test_error_status_code(self, rf):
        request = rf.get("/")
        resp = error(request, "bad data")
        assert resp.status_code == 400

    def test_error_escapes_html(self, rf):
        request = rf.get("/")
        resp = error(request, "<script>alert(1)</script>")
        assert b"<script>" not in resp.content
        assert b"&lt;script&gt;" in resp.content

    def test_error_contains_meta_tag(self, rf):
        request = rf.get("/")
        resp = error(request, "msg")
        assert b"$$RETURN_ERROR" in resp.content


class TestHtmlTemplates:
    def test_new_row_ok_html_template(self):
        assert "$$RETURN_NEW_ROW_OK" in _NEW_ROW_OK_HTML

    def test_update_row_ok_html_template(self):
        assert "$$RETURN_UPDATE_ROW_OK" in _UPDATE_ROW_OK_HTML

    def test_delete_row_ok_html_template(self):
        assert "$$RETURN_OK" in _DELETE_ROW_OK_HTML

    def test_error_html_template_format(self):
        rendered = _ERROR_HTML_TEMPLATE.format(body="test error")
        assert "$$RETURN_ERROR" in rendered
        assert "test error" in rendered
