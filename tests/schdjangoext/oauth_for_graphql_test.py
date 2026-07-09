from unittest.mock import MagicMock, patch

import pytest


try:
    from pytigon_lib.schdjangoext.oauth_for_graphql import (
        OAuth2ProtectedGraph,
        OAuth2ProtectedResourceMixin,
        _authenticate_jwt,
    )
    _IMPORT_OK = True
except (ImportError, RuntimeError):
    _IMPORT_OK = False


pytestmark = pytest.mark.skipif(not _IMPORT_OK, reason="Cannot import oauth_for_graphql module")


class TestAuthenticateJWT:
    def test_no_token_returns_none(self):
        request = MagicMock()
        with patch("pytigon_lib.schdjangoext.oauth_for_graphql.get_http_authorization", return_value=None):
            result = _authenticate_jwt(request)
            assert result is None

    def test_valid_token_returns_user(self):
        request = MagicMock()
        user = MagicMock()
        with patch("pytigon_lib.schdjangoext.oauth_for_graphql.get_http_authorization", return_value="valid_token"):
            with patch("pytigon_lib.schdjangoext.oauth_for_graphql.get_payload", return_value={"username": "testuser"}):
                with patch("django.contrib.auth.get_user_model") as mock_get_model:
                    mock_queryset = MagicMock()
                    mock_queryset.filter.return_value.first.return_value = user
                    mock_get_model.return_value.objects = mock_queryset
                    result = _authenticate_jwt(request)
                    assert result is user

    def test_jwt_exception_returns_none(self):
        request = MagicMock()
        with patch("pytigon_lib.schdjangoext.oauth_for_graphql.get_http_authorization", return_value="bad_token"):
            with patch("pytigon_lib.schdjangoext.oauth_for_graphql.get_payload", side_effect=Exception("invalid")):
                result = _authenticate_jwt(request)
                assert result is None

    def test_import_error_returns_none(self):
        request = MagicMock()
        import builtins
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if "graphql_jwt" in name:
                raise ImportError("no graphql_jwt")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            pass


class TestOAuth2ProtectedResourceMixin:
    def test_options_request_bypasses_auth(self):
        view = OAuth2ProtectedResourceMixin()
        view.request = MagicMock()
        view.request.method = "OPTIONS"
        view.dispatch = MagicMock(return_value="response")
        with patch("graphene_django.views.GraphQLView.dispatch", return_value="response"):
            view.dispatch = lambda req, *a, **k: "options_response"
            assert view.dispatch(view.request) == "options_response"

    def test_auth_failure_returns_401(self):
        view = OAuth2ProtectedResourceMixin()
        view.request = MagicMock()
        view.request.method = "GET"
        view.request.user = MagicMock()
        view.request.user.is_authenticated = False
        view.request.resource_owner = None
        view.verify_request = MagicMock(return_value=(False, MagicMock(user=None)))

        with patch("pytigon_lib.schdjangoext.oauth_for_graphql._authenticate_jwt", return_value=None):
            from django.http import JsonResponse
            response = view.dispatch(view.request)
            assert response.status_code == 401


class TestOAuth2ProtectedGraph:
    def test_is_subclass_of_mixin_and_graphql_view(self):
        assert issubclass(OAuth2ProtectedGraph, OAuth2ProtectedResourceMixin)

    def test_as_view_returns_callable(self):
        result = OAuth2ProtectedGraph.as_view()
        assert callable(result)
