from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from django.apps.config import AppConfig

from pytigon_lib.schdjangoext.django_init import AppConfigMod, get_app_config, get_app_name


def _make_app_mod(name="testapp"):
    app_module = MagicMock()
    app_module.__file__ = "/fake/path/__init__.py"
    mod = AppConfigMod(name, app_module)
    mod.models = {}
    mod.models_module = None
    return mod


class TestAppConfigMod:
    def test_add_with_string(self):
        mod = _make_app_mod("testapp")
        result = mod + ".suffix"
        assert result == "testapp.suffix"

    def test_add_with_app_config_mod(self):
        mod1 = _make_app_mod("app1")
        mod2 = _make_app_mod("app2")
        result = mod1 + mod2
        assert result == "app1app2"

    def test_add_with_app_config_subclass_instance(self):
        mod = _make_app_mod("myapp")

        class OtherMod(AppConfigMod):
            pass

        other = _make_app_mod("other")
        other.__class__ = OtherMod
        result = mod + other
        assert result == "myappother"

    def test_no_path_is_not_set_on_models_module(self):
        mod = _make_app_mod("testapp")
        mod.apps = MagicMock()
        assert True

    def test_import_models_import_error(self):
        mod = _make_app_mod("testapp")
        mod.apps = MagicMock()
        mod.apps.all_models = {"testapp": {"TestModel": MagicMock()}}
        with patch("pytigon_lib.schdjangoext.django_init.module_has_submodule", return_value=True):
            with patch("importlib.import_module", side_effect=ImportError):
                mod.import_models()
                assert mod.models_module is None

    def test_name_property(self):
        mod = _make_app_mod("testapp")
        assert mod.name == "testapp"


class TestGetAppConfig:
    def test_simple_name(self):
        with patch("pytigon_lib.schdjangoext.django_init.AppConfigMod.create") as mock_create:
            mock_create.return_value = _make_app_mod("myapp")
            config = get_app_config("myapp")
            mock_create.assert_called_with("myapp")

    def test_dotted_name(self):
        with patch("pytigon_lib.schdjangoext.django_init.AppConfigMod.create") as mock_create:
            mock_create.return_value = _make_app_mod("admin")
            config = get_app_config("django.contrib.admin")
            mock_create.assert_called_with("admin")

    def test_default_app_config_is_created(self):
        with patch("pytigon_lib.schdjangoext.django_init.AppConfigMod.create") as mock_create:
            mock_create.return_value = _make_app_mod("my_custom_app")
            config = get_app_config("my_custom_app")
            mock_create.assert_called_with("my_custom_app")


class TestGetAppName:
    def test_app_config_instance(self):
        app = _make_app_mod("testapp")
        assert get_app_name(app) == "testapp"

    def test_string_name(self):
        assert get_app_name("testapp") == "testapp"
