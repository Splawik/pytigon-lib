from unittest.mock import MagicMock, patch

# Pytest tests
import pytest

from pytigon_lib.schhttptools.rest_client import *


@pytest.fixture
def mock_httpx():
    """Intercept the pooled httpx.Client that get_rest_client() builds."""
    client = MagicMock()
    client.delete.return_value.status_code = 204
    client.delete.return_value.json.return_value = {}
    client.post.return_value.json.return_value = {"access_token": "new_access_token"}
    client.post.return_value.status_code = 200
    with patch("pytigon_lib.schhttptools.rest_client.httpx.Client", return_value=client):
        yield client


def test_get_rest_client(mock_httpx):
    client_mock = mock_httpx

    refresh_token = "test_refresh_token"
    client = get_rest_client("http://127.0.0.1:8000", refresh_token)

    # Test delete request
    response = client(httpx.delete, "/api/otkernel/1/measurement/")
    assert response.status_code == 204
    assert response.json() == {}

    # Test post request
    client_mock.post.return_value.json.return_value = {"data": {"hight": 20}}
    client_mock.post.return_value.status_code = 201

    response = client(
        httpx.post, "/api/otkernel/1/measurement/", json={"data": {"hight": 20}}
    )
    assert response.status_code == 201
    assert response.json() == {"data": {"hight": 20}}


def test_get_rest_client_failure(mock_httpx):
    client_mock = mock_httpx

    # Mock token refresh failure
    client_mock.post.return_value.raise_for_status.side_effect = httpx.HTTPError(
        "Token refresh failed"
    )

    refresh_token = "test_refresh_token"
    client = get_rest_client("http://127.0.0.1:8000", refresh_token)

    # Test delete request failure
    response = client(httpx.delete, "/api/otkernel/1/measurement/")
    assert response is None
