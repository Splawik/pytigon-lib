from unittest.mock import MagicMock, patch

import pytest
from django.http import HttpResponse
from django.test import RequestFactory

from pytigon_lib.schviews.perms import (
    default_block,
    filter_by_permissions,
    get_anonymous,
    has_the_right,
    make_perms_test_fun,
    make_perms_url_test_fun,
)


@pytest.fixture
def rf():
    return RequestFactory()


class TestFilterByPermissions:
    def test_model_has_method_calls_it(self):
        mock_model = MagicMock()
        mock_model.filter_by_permissions.return_value = "filtered_qs"
        result = filter_by_permissions("view", mock_model, "qs", "request")
        mock_model.filter_by_permissions.assert_called_once_with("view", "qs", "request")
        assert result == "filtered_qs"

    def test_model_no_method_returns_original(self):
        result = filter_by_permissions("view", object(), "qs_original", "request")
        assert result == "qs_original"


class TestHasTheRight:
    def test_model_has_method_calls_it(self):
        mock_model = MagicMock()
        mock_model.has_the_right.return_value = False
        result = has_the_right("view", mock_model, {"pk": 1}, "req")
        mock_model.has_the_right.assert_called_once_with("view", {"pk": 1}, "req")
        assert result is False

    def test_model_no_method_returns_true(self):
        result = has_the_right("view", object(), {}, "req")
        assert result is True


class TestGetAnonymous:
    def setup_method(self):
        try:
            import pytigon_lib.schviews.perms as perms_mod
            perms_mod._ANONYMOUS_PK = None
        except Exception:
            pass

    @patch("pytigon_lib.schviews.perms.authenticate")
    def test_creates_anonymous_user(self, mock_auth):
        mock_user = MagicMock()
        mock_user.pk = 7
        mock_auth.return_value = mock_user
        try:
            import pytigon_lib.schviews.perms as perms_mod
            perms_mod._ANONYMOUS_PK = None
            result = get_anonymous()
            assert result is mock_user
            mock_auth.assert_called_once_with(username="AnonymousUser", password="AnonymousUser")
        finally:
            pass

    @patch("pytigon_lib.schviews.perms.authenticate")
    def test_caches_pk_and_refetches_instance(self, mock_auth):
        mock_user = MagicMock()
        mock_user.pk = 7
        mock_auth.return_value = mock_user
        try:
            import pytigon_lib.schviews.perms as perms_mod
            perms_mod._ANONYMOUS_PK = None
            result1 = get_anonymous()
            result2 = get_anonymous()
            # Only the pk is cached: authenticate runs once, the instance is
            # re-fetched per call so a stale User object is never handed out.
            assert mock_auth.call_count == 1
            assert result1 is mock_user
            assert result2 is not mock_user
        finally:
            pass

    @patch("pytigon_lib.schviews.perms.authenticate")
    def test_auth_failure_returns_none(self, mock_auth):
        mock_auth.side_effect = RuntimeError("auth failed")
        try:
            import pytigon_lib.schviews.perms as perms_mod
            perms_mod._ANONYMOUS_PK = None
            result = get_anonymous()
            assert result is None
        finally:
            pass


class TestDefaultBlock:
    @patch("pytigon_lib.schviews.perms.render_to_response")
    def test_returns_401(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("blocked", status=401)
        default_block(rf.get("/"))
        mock_rtr.assert_called_once()
        call_args = mock_rtr.call_args[0]
        assert call_args[0] == "schsys/no_perm.html"
        assert mock_rtr.call_args[1]["status"] == 401


class TestMakePermsUrlTestFun:
    @patch("django.conf.settings.PUBLIC", False)
    @patch("pytigon_lib.schviews.perms.get_app_name")
    @patch("django.conf.settings.INSTALLED_APPS", ["test_app"])
    def test_no_policy_blocks_anonymous(self, mock_get_app_name, rf):
        mock_get_app_name.return_value = "test_app"
        mock_fun = MagicMock(return_value=HttpResponse("ok"))
        block_view = MagicMock(return_value=HttpResponse("blocked", status=401))
        wrapper = make_perms_url_test_fun("test_app", mock_fun, block_view)
        resp = wrapper(rf.get("/"))
        mock_fun.assert_not_called()
        block_view.assert_called_once()
        assert resp.status_code == 401

    @patch("django.conf.settings.PUBLIC", False)
    @patch("pytigon_lib.schviews.perms.get_app_name")
    @patch("django.conf.settings.INSTALLED_APPS", ["test_app"])
    def test_no_policy_allows_authenticated(self, mock_get_app_name, rf):
        mock_get_app_name.return_value = "test_app"
        mock_fun = MagicMock(return_value=HttpResponse("ok"))
        block_view = MagicMock(return_value=HttpResponse("blocked", status=401))
        wrapper = make_perms_url_test_fun("test_app", mock_fun, block_view)
        req = rf.get("/")
        req.user = MagicMock(is_authenticated=True, is_staff=False)
        wrapper(req)
        mock_fun.assert_called_once()
        block_view.assert_not_called()

    @patch("django.conf.settings.PUBLIC", False)
    @patch("django.conf.settings.STAFF_ONLY_APPS", ("schinstall",))
    @patch("pytigon_lib.schviews.perms.get_app_name")
    @patch("django.conf.settings.INSTALLED_APPS", ["schinstall"])
    def test_staff_only_app_blocks_non_staff(self, mock_get_app_name, rf):
        mock_get_app_name.return_value = "schinstall"
        mock_fun = MagicMock(return_value=HttpResponse("ok"))
        block_view = MagicMock(return_value=HttpResponse("blocked", status=401))
        wrapper = make_perms_url_test_fun("schinstall", mock_fun, block_view)
        req = rf.get("/")
        req.user = MagicMock(is_authenticated=True, is_staff=False)
        wrapper(req)
        mock_fun.assert_not_called()
        block_view.assert_called_once()

    @patch("django.conf.settings.PUBLIC", False)
    @patch("django.conf.settings.STAFF_ONLY_APPS", ("schinstall",))
    @patch("pytigon_lib.schviews.perms.get_app_name")
    @patch("django.conf.settings.INSTALLED_APPS", ["schinstall"])
    def test_staff_only_app_allows_staff(self, mock_get_app_name, rf):
        mock_get_app_name.return_value = "schinstall"
        mock_fun = MagicMock(return_value=HttpResponse("ok"))
        block_view = MagicMock(return_value=HttpResponse("blocked", status=401))
        wrapper = make_perms_url_test_fun("schinstall", mock_fun, block_view)
        req = rf.get("/")
        req.user = MagicMock(is_authenticated=True, is_staff=True)
        wrapper(req)
        mock_fun.assert_called_once()

    @patch("django.conf.settings.PUBLIC", True)
    @patch("django.conf.settings.STAFF_ONLY_APPS", ("schinstall",))
    @patch("pytigon_lib.schviews.perms.get_app_name")
    @patch("django.conf.settings.INSTALLED_APPS", ["schinstall"])
    def test_staff_only_app_is_enforced_even_on_public_site(
        self, mock_get_app_name, rf
    ):
        """A PUBLIC site must not expose the installer to anonymous users."""
        mock_get_app_name.return_value = "schinstall"
        mock_fun = MagicMock(return_value=HttpResponse("ok"))
        block_view = MagicMock(return_value=HttpResponse("blocked", status=401))
        wrapper = make_perms_url_test_fun("schinstall", mock_fun, block_view)
        wrapper(rf.get("/"))
        mock_fun.assert_not_called()
        block_view.assert_called_once()


class TestMakePermsTestFun:
    def test_no_request_user_skips_check(self):
        mock_fun = MagicMock(return_value=HttpResponse("ok"))
        wrapper = make_perms_test_fun("app", MagicMock(), "app.view_model", mock_fun)
        req = MagicMock(spec=[])
        wrapper(req)
        mock_fun.assert_called_once()

    def test_user_has_perm_calls_fun(self):
        mock_fun = MagicMock(return_value=HttpResponse("ok"))
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.has_perm.return_value = True

        mock_model = MagicMock()
        mock_model.has_the_right.return_value = True

        wrapper = make_perms_test_fun("app", mock_model, "app.view_model", mock_fun)
        req = MagicMock()
        req.user = mock_user
        wrapper(req)
        mock_fun.assert_called_once()
        mock_user.has_perm.assert_called_once_with("app.view_model")

    def test_user_no_perm_blocks(self, rf):
        mock_fun = MagicMock(return_value=HttpResponse("ok"))
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.has_perm.return_value = False

        block_view = MagicMock(return_value=HttpResponse("blocked", status=401))
        mock_model = MagicMock()

        wrapper = make_perms_test_fun("app", mock_model, "app.view_model", mock_fun, block_view)
        req = MagicMock()
        req.user = mock_user
        wrapper(req)
        mock_fun.assert_not_called()
        block_view.assert_called_once()

    def test_has_the_right_false_blocks(self, rf):
        mock_fun = MagicMock(return_value=HttpResponse("ok"))
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.has_perm.return_value = True

        mock_model = MagicMock()
        mock_model.has_the_right.return_value = False

        block_view = MagicMock(return_value=HttpResponse("blocked", status=401))

        wrapper = make_perms_test_fun("app", mock_model, "app.view_model", mock_fun, block_view)
        req = MagicMock()
        req.user = mock_user
        wrapper(req)
        mock_fun.assert_not_called()
        block_view.assert_called_once()

    @patch("pytigon_lib.schviews.perms.get_anonymous")
    def test_unauthenticated_user_falls_back_to_anonymous(self, mock_ga):
        mock_fun = MagicMock(return_value=HttpResponse("ok"))
        mock_anon = MagicMock()
        mock_anon.is_authenticated = False
        mock_anon.has_perm.return_value = True
        mock_ga.return_value = mock_anon

        mock_user = MagicMock()
        mock_user.is_authenticated = False

        mock_model = MagicMock()
        mock_model.has_the_right.return_value = True

        wrapper = make_perms_test_fun("app", mock_model, "app.view_model", mock_fun)
        req = MagicMock()
        req.user = mock_user
        wrapper(req)
        mock_ga.assert_called_once()

    @patch("pytigon_lib.schviews.perms.get_anonymous")
    def test_anonymous_fallback_none_uses_request_user(self, mock_ga):
        mock_fun = MagicMock(return_value=HttpResponse("ok"))
        mock_ga.return_value = None

        mock_user = MagicMock()
        mock_user.is_authenticated = False
        mock_user.has_perm.return_value = True

        mock_model = MagicMock()
        mock_model.has_the_right.return_value = True

        wrapper = make_perms_test_fun("app", mock_model, "app.view_model", mock_fun)
        req = MagicMock()
        req.user = mock_user
        wrapper(req)
        assert mock_user.has_perm.called
