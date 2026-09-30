"""Extra tests for :mod:`pytigon_lib.schhttptools.rest_client`."""
from unittest.mock import MagicMock, patch

import httpx
import pytest

from pytigon_lib.schhttptools.rest_client import get_rest_client


def _make_client_mock(token="new_token"):
    """Build a mock for the module-level ``httpx.Client``.

    ``get_rest_client`` now builds one pooled ``httpx.Client`` per returned
    callable, so the tests intercept the client rather than the module-level
    ``httpx.get``/``httpx.post`` helpers.
    """
    client = MagicMock()
    client.post.return_value.json.return_value = {"access_token": token}
    client.post.return_value.status_code = 200
    client.post.return_value.raise_for_status = MagicMock()
    for name in ("get", "post", "put", "patch", "delete"):
        getattr(client, name).return_value.status_code = 200
    client.get.return_value.json.return_value = {"data": "ok"}
    return client


class TestGetRestClientExtra:
    def test_returns_callable(self):
        client = get_rest_client("http://example.com", "refresh")
        assert callable(client)

    def test_uses_a_pooled_client_with_timeout(self):
        with patch(
            "pytigon_lib.schhttptools.rest_client.httpx.Client",
            return_value=_make_client_mock(),
        ) as mock_client_cls:
            get_rest_client("http://example.com", "refresh")
            assert mock_client_cls.call_args.kwargs["timeout"] > 0

    @patch("pytigon_lib.schhttptools.rest_client.httpx.Client")
    def test_client_with_access_token(self, mock_client_cls):
        client_mock = _make_client_mock()
        mock_client_cls.return_value = client_mock

        client = get_rest_client("http://example.com", "refresh")
        response = client(httpx.get, "/api/data")
        assert response is not None
        # No token yet, so a token refresh must have happened.
        assert client_mock.post.called

    @patch("pytigon_lib.schhttptools.rest_client.httpx.Client")
    def test_client_401_refreshes(self, mock_client_cls):
        client_mock = _make_client_mock()
        mock_client_cls.return_value = client_mock

        client = get_rest_client("http://api.com", "refresh")
        # Prime the token so the next call takes the authenticated path.
        client(httpx.get, "/data")
        client_mock.post.reset_mock()
        unauthorized = MagicMock(status_code=401)
        client_mock.get.side_effect = [unauthorized, MagicMock(status_code=200)]
        client(httpx.get, "/data")
        assert client_mock.post.called

    @patch("pytigon_lib.schhttptools.rest_client.httpx.Client")
    def test_token_refresh_failure(self, mock_client_cls):
        client_mock = _make_client_mock()
        client_mock.post.side_effect = httpx.RequestError("token failure")
        mock_client_cls.return_value = client_mock

        client = get_rest_client("http://api.com", "refresh")
        response = client(httpx.get, "/data")
        assert response is None

    @patch("pytigon_lib.schhttptools.rest_client.httpx.Client")
    def test_client_delete(self, mock_client_cls):
        client_mock = _make_client_mock()
        client_mock.delete.return_value.status_code = 204
        mock_client_cls.return_value = client_mock

        client = get_rest_client("http://api.com", "refresh")
        response = client(httpx.delete, "/remove/1")
        assert response.status_code == 204

    @patch("pytigon_lib.schhttptools.rest_client.httpx.Client")
    def test_client_patch(self, mock_client_cls):
        client_mock = _make_client_mock()
        mock_client_cls.return_value = client_mock

        client = get_rest_client("http://api.com", "refresh")
        response = client(httpx.patch, "/update/1", json={"field": "value"})
        assert response.status_code == 200

    @patch("pytigon_lib.schhttptools.rest_client.httpx.Client")
    def test_request_error_returns_none(self, mock_client_cls):
        client_mock = _make_client_mock()
        mock_client_cls.return_value = client_mock

        client = get_rest_client("http://api.com", "refresh")
        # Prime the token so the request goes down the authenticated path.
        client(httpx.get, "/data")
        client_mock.get.side_effect = httpx.RequestError("request error")
        response = client(httpx.get, "/data")
        assert response is None

    @patch("pytigon_lib.schhttptools.rest_client.httpx.Client")
    def test_http_status_error_is_caught(self, mock_client_cls):
        client_mock = _make_client_mock()
        mock_client_cls.return_value = client_mock

        client = get_rest_client("http://api.com", "refresh")
        # raise_for_status() raises HTTPStatusError, which is an HTTPError but
        # not a RequestError; the old except clause let it escape.
        client_mock.post.side_effect = httpx.HTTPStatusError(
            "500", request=MagicMock(), response=MagicMock()
        )
        response = client(httpx.get, "/data")
        assert response is None

    @patch("pytigon_lib.schhttptools.rest_client.httpx.Client")
    def test_caller_headers_are_not_mutated(self, mock_client_cls):
        mock_client_cls.return_value = _make_client_mock()

        client = get_rest_client("http://api.com", "refresh")
        headers = {"X-Test": "1"}
        client(httpx.get, "/data", headers=headers)
        assert headers == {"X-Test": "1"}

    @patch("pytigon_lib.schhttptools.rest_client.httpx.Client")
    def test_post_request(self, mock_client_cls):
        mock_client_cls.return_value = _make_client_mock()

        client = get_rest_client("http://api.com", "refresh")
        response = client(httpx.post, "/create", json={"name": "test"})
        assert response.status_code == 200

    @patch("pytigon_lib.schhttptools.rest_client.httpx.Client")
    def test_client_put(self, mock_client_cls):
        mock_client_cls.return_value = _make_client_mock()

        client = get_rest_client("http://api.com", "refresh")
        response = client(httpx.put, "/replace/1", json={"x": "y"})
        assert response.status_code == 200
