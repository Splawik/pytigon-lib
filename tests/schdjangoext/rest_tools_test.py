from unittest.mock import MagicMock, patch

import pytest
from django.db import models as dj_models

from pytigon_lib.schdjangoext.rest_tools import create_api_for_models


def _create_module_and_models(name, model_names):
    import types
    mod = types.ModuleType(name)

    for mname in model_names:
        model = type(mname, (dj_models.Model,), {
            "__module__": name,
            "Meta": type("Meta", (), {"app_label": name.split(".")[0]}),
        })
        setattr(mod, mname, model)

    return mod


class TestCreateApiForModels:
    def test_creates_urlpatterns(self):
        mod = _create_module_and_models("testapp_rest1.models", ["TestModel1", "TestModel2"])
        urlpatterns = []
        create_api_for_models(mod, urlpatterns)
        assert len(urlpatterns) == 4

    def test_creates_list_and_detail_urls(self):
        mod = _create_module_and_models("testapp_rest2.models", ["TestModel1"])
        urlpatterns = []
        create_api_for_models(mod, urlpatterns)
        pattern_strs = [str(p.pattern) for p in urlpatterns]
        assert any("testmodel1s/" in p for p in pattern_strs)
        assert any("<int:pk>" in p for p in pattern_strs)

    def test_include_filter_only_specified_models(self):
        mod = _create_module_and_models("testapp_rest3.models", ["TestModel1", "TestModel2"])
        urlpatterns = []
        create_api_for_models(mod, urlpatterns, include=["TestModel1"])
        assert len(urlpatterns) == 2

    def test_exclude_filter_removes_specified_models(self):
        mod = _create_module_and_models("testapp_rest4.models", ["TestModel1", "TestModel2"])
        urlpatterns = []
        create_api_for_models(mod, urlpatterns, exclude=["TestModel1"])
        assert len(urlpatterns) == 2

    def test_skips_non_model_attrs(self):
        mod = _create_module_and_models("testapp_rest5.models", ["TestModel1"])
        mod.some_string = "hello"
        urlpatterns = []
        create_api_for_models(mod, urlpatterns)
        assert len(urlpatterns) == 2

    def test_skips_wrong_module_model(self):
        mod = _create_module_and_models("testapp_rest6.models", ["TestModel1"])
        mod.TestModel1.__module__ = "other_app.models"
        urlpatterns = []
        create_api_for_models(mod, urlpatterns)
        assert len(urlpatterns) == 0

    def test_custom_permissions_applied(self):
        mod = _create_module_and_models("testapp_rest7.models", ["TestModel1"])
        urlpatterns = []
        custom_perms = [MagicMock()]
        create_api_for_models(
            mod, urlpatterns,
            permission_classes_list_create=custom_perms,
            permission_classes_update_destroy=custom_perms,
        )
        assert len(urlpatterns) == 2

    def test_empty_module_no_models(self):
        import types
        mod = types.ModuleType("empty_rest.models")
        urlpatterns = []
        create_api_for_models(mod, urlpatterns)
        assert len(urlpatterns) == 0

    def test_include_empty_list_adds_all(self):
        mod = _create_module_and_models("testapp_rest8.models", ["TestModel1"])
        urlpatterns = []
        create_api_for_models(mod, urlpatterns, include=[])
        assert len(urlpatterns) == 2

    def test_exclude_empty_list_adds_all(self):
        mod = _create_module_and_models("testapp_rest9.models", ["TestModel1"])
        urlpatterns = []
        create_api_for_models(mod, urlpatterns, exclude=[])
        assert len(urlpatterns) == 2
