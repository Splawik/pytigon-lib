import logging
from unittest.mock import MagicMock, patch

import pytest


try:
    from pytigon_lib.schdjangoext.allauth import SocialAccountAdapter
    _IMPORT_OK = True
except (ImportError, RuntimeError):
    _IMPORT_OK = False


pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="Cannot import allauth module")


class TestSocialAccountAdapter:
    @pytest.fixture
    def adapter(self):
        return SocialAccountAdapter()

    def test_authentication_error_logs_correctly(self, adapter):
        request = MagicMock()
        with patch.object(logging.getLogger("pytigon"), "error") as mock_error:
            adapter.authentication_error(
                request=request,
                provider_id="google",
                error="auth_failed",
                exception=Exception("network error"),
                extra_context={"key": "value"},
            )
            mock_error.assert_called_once()
            logged_data = mock_error.call_args[0][0]
            assert logged_data["title"] == "SocialAccount authentication error!"
            assert logged_data["provider_id"] == "google"
            assert logged_data["error"] == "auth_failed"
            assert "network error" in logged_data["exception"]
            assert logged_data["extra_context"] == {"key": "value"}

    def test_authentication_error_all_values_present(self, adapter):
        request = MagicMock()
        with patch.object(logging.getLogger("pytigon"), "error") as mock_error:
            adapter.authentication_error(
                request=request,
                provider_id="facebook",
                error=ValueError("bad request"),
                exception=RuntimeError("internal"),
                extra_context={},
            )
            logged = mock_error.call_args[0][0]
            assert "facebook" in logged["provider_id"]
            assert "bad request" in logged["error"]

    def test_authentication_error_exception_handling(self, adapter):
        request = MagicMock()
        with patch.object(logging.getLogger("pytigon"), "error") as mock_error:
            mock_error.side_effect = Exception("logger failed")
            with patch.object(logging.getLogger("pytigon"), "error") as mock_error2:
                adapter.authentication_error(
                    request=request,
                    provider_id="test",
                    error="err",
                    exception=Exception("ex"),
                    extra_context={},
                )

    def test_authentication_error_none_values_serialized(self, adapter):
        request = MagicMock()
        with patch.object(logging.getLogger("pytigon"), "error") as mock_error:
            adapter.authentication_error(
                request=request,
                provider_id=None,
                error=None,
                exception=None,
                extra_context=None,
            )
            logged = mock_error.call_args[0][0]
            assert logged["provider_id"] is None

    def test_authentication_error_different_providers(self, adapter):
        request = MagicMock()
        for provider in ["google", "facebook", "github", "twitter"]:
            with patch.object(logging.getLogger("pytigon"), "error") as mock_error:
                adapter.authentication_error(
                    request=request,
                    provider_id=provider,
                    error="test",
                    exception=Exception("test"),
                    extra_context={},
                )
                logged = mock_error.call_args[0][0]
                assert logged["provider_id"] == provider

    def test_logger_name_is_pytigon(self, adapter):
        assert logging.getLogger("pytigon").name == "pytigon"

    def test_authentication_error_returns_none(self, adapter):
        request = MagicMock()
        with patch.object(logging.getLogger("pytigon"), "error"):
            result = adapter.authentication_error(
                request=request,
                provider_id="test",
                error="err",
                exception=Exception("ex"),
                extra_context={},
            )
            assert result is None
