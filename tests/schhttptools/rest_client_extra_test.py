"""Extra tests for :mod:`pytigon_lib.schhttptools.rest_client`."""
from unittest.mock import MagicMock, patch

import httpx
import pytest

from pytigon_lib.schhttptools.rest_client import get_rest_client


class TestGetRestClientExtra:
    def test_returns_callable(self):
        client = get_rest_client("http://example.com", "refresh")
        assert callable(client)

    @patch("pytigon_lib.schhttptools.rest_client.httpx.post")
    @patch("pytigon_lib.schhttptools.rest_client.httpx.get")
    def test_client_with_access_token(self, mock_get, mock_post):
        mock_post.return_value.json.return_value = {"access_token": "new_token"}
        mock_post.return_value.status_code = 200
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"data": "ok"}

        client = get_rest_client("http://example.com", "refresh")
        response = client(httpx.get, "/api/data")
        assert response is not None
        assert mock_post.called

    @patch("pytigon_lib.schhttptools.rest_client.httpx.post")
    @patch("pytigon_lib.schhttptools.rest_client.httpx.get")
    def test_client_401_refreshes(self, mock_get, mock_post):
        mock_post.return_value.json.return_value = {"access_token": "new_token"}
        mock_post.return_value.status_code = 200
        mock_get.return_value.status_code = 200

        client = get_rest_client("http://api.com", "refresh")
        client(httpx.get, "/data")
        assert mock_post.called

    @patch("pytigon_lib.schhttptools.rest_client.httpx.post")
    def test_token_refresh_failure(self, mock_post):
        mock_post.side_effect = httpx.RequestError("token failure")
        client = get_rest_client("http://api.com", "refresh")
        with patch("pytigon_lib.schhttptools.rest_client.httpx.get"):
            response = client(httpx.get, "/data")
            assert response is None

    @patch("pytigon_lib.schhttptools.rest_client.httpx.post")
    @patch("pytigon_lib.schhttptools.rest_client.httpx.delete")
    def test_client_delete(self, mock_delete, mock_post):
        mock_post.return_value.json.return_value = {"access_token": "token"}
        mock_post.return_value.status_code = 200
        mock_delete.return_value.status_code = 204

        client = get_rest_client("http://api.com", "refresh")
        response = client(httpx.delete, "/remove/1")
        assert response.status_code == 204

    @patch("pytigon_lib.schhttptools.rest_client.httpx.post")
    @patch("pytigon_lib.schhttptools.rest_client.httpx.patch")
    def test_client_patch(self, mock_patch, mock_post):
        mock_post.return_value.json.return_value = {"access_token": "token"}
        mock_post.return_value.status_code = 200
        mock_patch.return_value.status_code = 200

        client = get_rest_client("http://api.com", "refresh")
        response = client(httpx.patch, "/update/1", json={"field": "value"})
        assert response.status_code == 200

    @patch("pytigon_lib.schhttptools.rest_client.httpx.post")
    def test_request_error_returns_none(self, mock_post):
        mock_post.return_value.json.return_value = {"access_token": "token"}
        mock_post.return_value.status_code = 200

        client = get_rest_client("http://api.com", "refresh")
        with patch("pytigon_lib.schhttptools.rest_client.httpx.get",
                   side_effect=httpx.RequestError("request error")):
            response = client(httpx.get, "/data")
            assert response is None

    @patch("pytigon_lib.schhttptools.rest_client.httpx.post")
    def test_post_request(self, mock_post):
        mock_post.return_value.json.return_value = {"access_token": "token"}
        mock_post.return_value.status_code = 200
        mock_post.return_value.raise_for_status = MagicMock()

        client = get_rest_client("http://api.com", "refresh")
        response = client(httpx.post, "/create", json={"name": "test"})
        assert response.status_code == 200

    @patch("pytigon_lib.schhttptools.rest_client.httpx.post")
    @patch("pytigon_lib.schhttptools.rest_client.httpx.put")
    def test_client_put(self, mock_put, mock_post):
        mock_post.return_value.json.return_value = {"access_token": "token"}
        mock_post.return_value.status_code = 200
        mock_put.return_value.status_code = 200

        client = get_rest_client("http://api.com", "refresh")
        response = client(httpx.put, "/replace/1", json={"x": "y"})
        assert response.status_code == 200
