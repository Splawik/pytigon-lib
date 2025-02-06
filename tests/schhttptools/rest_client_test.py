from pytigon_lib.schhttptools.rest_client import *

# Pytest tests
import pytest
from unittest.mock import Mock, patch


@pytest.fixture
def mock_httpx():
    with patch("httpx.post") as mock_post, patch("httpx.delete") as mock_delete:
        yield mock_post, mock_delete


def test_get_rest_client(mock_httpx):
    mock_post, mock_delete = mock_httpx

    # Mock token refresh response
    mock_post.return_value.json.return_value = {"access_token": "new_access_token"}
    mock_post.return_value.status_code = 200

    # Mock delete response
    mock_delete.return_value.status_code = 204
    mock_delete.return_value.json.return_value = {}

    refresh_token = "test_refresh_token"
    client = get_rest_client("http://127.0.0.1:8000", refresh_token)

    # Test delete request
    response = client(httpx.delete, "/api/otkernel/1/measurement/")
    assert response.status_code == 204
    assert response.json() == {}

    # Test post request
    mock_post.return_value.json.return_value = {"data": {"hight": 20}}
    mock_post.return_value.status_code = 201

    response = client(
        httpx.post, "/api/otkernel/1/measurement/", json={"data": {"hight": 20}}
    )
    assert response.status_code == 201
    assert response.json() == {"data": {"hight": 20}}


def test_get_rest_client_failure(mock_httpx):
    mock_post, mock_delete = mock_httpx

    # Mock token refresh failure
    mock_post.return_value.raise_for_status.side_effect = httpx.RequestError(
        "Token refresh failed"
    )

    refresh_token = "test_refresh_token"
    client = get_rest_client("http://127.0.0.1:8000", refresh_token)

    # Test delete request failure
    response = client(httpx.delete, "/api/otkernel/1/measurement/")
    assert response is None
