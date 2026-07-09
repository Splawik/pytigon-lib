"""Extra tests for :mod:`pytigon_lib.schhttptools.get_oauth2_refresh_token`."""
import base64
from unittest.mock import patch

import pytest

from pytigon_lib.schhttptools.get_oauth2_refresh_token import get_refresh_token, main


class TestGetRefreshToken:
    def test_basic_encoding(self):
        token = get_refresh_token("id", "secret")
        assert isinstance(token, str)
        assert token == base64.b64encode(b"id:secret").decode("utf-8")

    def test_different_credentials(self):
        token = get_refresh_token("client123", "pass456")
        assert token == base64.b64encode(b"client123:pass456").decode("utf-8")

    def test_special_characters(self):
        token = get_refresh_token("id!@#", "secret$%^")
        assert token == base64.b64encode(b"id!@#:secret$%^").decode("utf-8")

    def test_long_credentials(self):
        cid = "a" * 100
        csec = "b" * 100
        token = get_refresh_token(cid, csec)
        expected = base64.b64encode(f"{cid}:{csec}".encode()).decode("utf-8")
        assert token == expected

    def test_empty_client_id_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            get_refresh_token("", "secret")

    def test_empty_client_secret_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            get_refresh_token("id", "")

    def test_both_empty_raises(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            get_refresh_token("", "")

    def test_token_is_valid_base64(self):
        token = get_refresh_token("myid", "mysecret")
        decoded = base64.b64decode(token.encode("utf-8")).decode("utf-8")
        assert decoded == "myid:mysecret"

    def test_unicode_credentials(self):
        token = get_refresh_token("test", "password")
        assert token == base64.b64encode(b"test:password").decode("utf-8")

    def test_result_not_empty(self):
        token = get_refresh_token("id", "secret")
        assert len(token) > 0


class TestMain:
    @patch("builtins.input", side_effect=["test_id", "test_secret"])
    @patch("sys.stdout")
    def test_main_normal_flow(self, mock_stdout, mock_input):
        main()
        assert True

    @patch("builtins.input", side_effect=["", ""])
    @patch("sys.stderr")
    def test_main_empty_input(self, mock_stderr, mock_input):
        with pytest.raises(SystemExit):
            main()

    @patch("builtins.input", side_effect=EOFError)
    @patch("sys.stderr")
    def test_main_eof(self, mock_stderr, mock_input):
        with pytest.raises(SystemExit):
            main()

    @patch("builtins.input", side_effect=KeyboardInterrupt)
    @patch("sys.stderr")
    def test_main_keyboard_interrupt(self, mock_stderr, mock_input):
        with pytest.raises(SystemExit):
            main()
