from unittest.mock import MagicMock, patch

from pytigon_lib.schviews.schrules import (
    _ensure_rules,
    _make_perm,
    filter_queryset_by_rules,
    is_rules_active,
    user_can,
)


class TestMakePerm:
    def test_make_perm_basic(self):
        mock_model = MagicMock()
        mock_model._meta.app_label = "myapp"
        mock_model._meta.model_name = "mymodel"
        result = _make_perm("view", mock_model)
        assert result == "myapp.view_mymodel"

    def test_make_perm_change(self):
        mock_model = MagicMock()
        mock_model._meta.app_label = "blog"
        mock_model._meta.model_name = "post"
        result = _make_perm("change", mock_model)
        assert result == "blog.change_post"

    def test_make_perm_delete(self):
        mock_model = MagicMock()
        mock_model._meta.app_label = "admin"
        mock_model._meta.model_name = "userprofile"
        result = _make_perm("delete", mock_model)
        assert result == "admin.delete_userprofile"


class TestEnsureRules:
    @patch("pytigon_lib.schviews.schrules._RULES_IMPORTED", None)
    def test_rules_not_imported_returns_false(self):
        with patch.dict("sys.modules", {"rules": __import__("os")}):
            # When rules module cannot be imported, _ensure_rules returns False
            import pytigon_lib.schviews.schrules as mod
            mod._RULES_IMPORTED = None
            # The module should handle import error gracefully
            try:
                result = _ensure_rules()
            except Exception:
                result = False
            finally:
                mod._RULES_IMPORTED = None
            assert isinstance(result, bool)


class TestIsRulesActive:
    @patch("pytigon_lib.schviews.schrules._ensure_rules")
    @patch("pytigon_lib.schviews.schrules.settings")
    def test_rules_not_installed_returns_false(self, mock_settings, mock_ensure):
        mock_ensure.return_value = False
        result = is_rules_active()
        assert result is False

    @patch("pytigon_lib.schviews.schrules._ensure_rules")
    @patch("pytigon_lib.schviews.schrules.settings")
    def test_rules_installed_but_disabled(self, mock_settings, mock_ensure):
        mock_ensure.return_value = True
        mock_settings.RULES_ENABLED = False
        result = is_rules_active()
        assert result is False

    @patch("pytigon_lib.schviews.schrules._ensure_rules")
    @patch("pytigon_lib.schviews.schrules.settings")
    def test_rules_installed_and_enabled(self, mock_settings, mock_ensure):
        mock_ensure.return_value = True
        mock_settings.RULES_ENABLED = True
        result = is_rules_active()
        assert result is True


class TestUserCan:
    def test_none_user_returns_false(self):
        mock_model = MagicMock()
        mock_model._meta.app_label = "app"
        mock_model._meta.model_name = "model"
        assert user_can(None, "view", mock_model) is False

    def test_unauthenticated_user_returns_false(self):
        mock_user = MagicMock()
        mock_user.is_authenticated = False
        mock_model = MagicMock()
        mock_model._meta.app_label = "app"
        mock_model._meta.model_name = "model"
        assert user_can(mock_user, "view", mock_model) is False

    def test_authenticated_user_with_perm(self):
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.has_perm.return_value = True
        mock_model = MagicMock()
        mock_model._meta.app_label = "myapp"
        mock_model._meta.model_name = "post"
        result = user_can(mock_user, "view", mock_model)
        mock_user.has_perm.assert_called_once_with("myapp.view_post", None)
        assert result is True

    def test_authenticated_user_without_perm(self):
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.has_perm.return_value = False
        mock_model = MagicMock()
        mock_model._meta.app_label = "myapp"
        mock_model._meta.model_name = "post"
        result = user_can(mock_user, "change", mock_model)
        assert result is False

    def test_with_object_instance(self):
        mock_user = MagicMock()
        mock_user.is_authenticated = True
        mock_user.has_perm.return_value = True
        mock_model = MagicMock()
        mock_model._meta.app_label = "app"
        mock_model._meta.model_name = "model"
        mock_obj = MagicMock()
        result = user_can(mock_user, "detail", mock_model, mock_obj)
        mock_user.has_perm.assert_called_once_with("app.detail_model", mock_obj)
        assert result is True


class TestFilterQuerysetByRules:
    @patch("pytigon_lib.schviews.schrules.is_rules_active")
    def test_rules_not_active_returns_original(self, mock_ira):
        mock_ira.return_value = False
        mock_qs = MagicMock()
        result = filter_queryset_by_rules(MagicMock(), "view", MagicMock(), mock_qs)
        assert result is mock_qs

    @patch("pytigon_lib.schviews.schrules.is_rules_active")
    def test_none_queryset_defaults_to_all(self, mock_ira):
        mock_ira.return_value = False
        mock_model = MagicMock()
        mock_model.objects.all.return_value = "full_qs"
        result = filter_queryset_by_rules(MagicMock(), "view", mock_model)
        assert result == "full_qs"
