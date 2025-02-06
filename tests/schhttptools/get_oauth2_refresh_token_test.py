from pytigon_lib.schhttptools.get_oauth2_refresh_token import *
import pytest


def test_get_refresh_token():
    client_id = "test_client_id"
    client_secret = "test_client_secret"
    expected_token = base64.b64encode(
        f"{client_id}:{client_secret}".encode("utf-8")
    ).decode("utf-8")

    assert get_refresh_token(client_id, client_secret) == expected_token


if __name__ == "__main__":
    pytest.main()
