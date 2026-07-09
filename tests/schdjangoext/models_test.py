from unittest.mock import MagicMock, patch

import pytest
from django import forms
from django.db import models


def import_or_skip(module_path, names):
    try:
        mod = __import__(module_path, fromlist=names)
        return tuple(getattr(mod, n) for n in names)
    except (ImportError, RuntimeError):
        pytest.skip(f"Cannot import {module_path}")




try:
    from pytigon_lib.schdjangoext.models import (
        AssociatedModel,
        CallProxy,
        JSONModel,
        OverwritableCallable,
        TreeModel,
        admin_register,
        extend_class,
        get_form,
        standard_table_action,
    )
    _MODEL_IMPORT_OK = True
except (ImportError, RuntimeError):
    _MODEL_IMPORT_OK = False


pytestmark = pytest.mark.skipif(not _MODEL_IMPORT_OK, reason="Cannot import models module")


class TestCallProxy:
    def test_init_with_no_extra_params(self):
        obj = MagicMock()
        proxy = CallProxy(obj, "method_name")
        assert proxy.obj is obj
        assert proxy.fun is obj.method_name
        assert proxy.parameters is None

    def test_init_with_extra_params(self):
        obj = MagicMock()
        proxy = CallProxy(obj, "method_name__param1__param2")
        assert proxy.parameters == ["param1", "param2"]

    def test_call_no_extra_params(self):
        obj = MagicMock()
        obj.method_name.return_value = "result"
        proxy = CallProxy(obj, "method_name")
        assert proxy.call("arg1") == "result"
        obj.method_name.assert_called_once_with("arg1")

    def test_call_with_extra_params(self):
        obj = MagicMock()
        obj.method_name.return_value = "result"
        proxy = CallProxy(obj, "method_name__param1__param2")
        assert proxy.call("arg1") == "result"
        obj.method_name.assert_called_once_with("param1", "param2", "arg1")


class TestJSONModelAttributeAccess:
    @pytest.fixture
    def json_instance(self):
        return JSONModel()

    def test_getattribute_json_field(self, json_instance):
        json_instance.jsondata = {"key1": "value1", "key2": 42}
        assert json_instance.json_key1 == "value1"
        assert json_instance.json_key2 == 42

    def test_getattribute_json_field_missing(self, json_instance):
        json_instance.jsondata = {}
        assert json_instance.json_missing is None

    def test_getattribute_json_field_null_jsondata(self, json_instance):
        json_instance.jsondata = None
        assert json_instance.json_anything is None

    def test_getattribute_call_proxy(self, json_instance):
        proxy = json_instance.call__some_method
        assert isinstance(proxy, CallProxy)

    def test_getattribute_call_proxy_with_params(self, json_instance):
        proxy = json_instance.call__method__p1__p2
        assert isinstance(proxy, CallProxy)
        assert proxy.parameters == ["p1", "p2"]

    def test_getattribute_regular_attr(self, json_instance):
        json_instance.pk = 1
        assert json_instance.pk == 1

    def test_setattribute_json_field_existing_data(self, json_instance):
        json_instance.jsondata = {"old": "val"}
        json_instance.json_new = "updated"
        assert json_instance.jsondata["new"] == "updated"
        assert json_instance.jsondata["old"] == "val"

    def test_setattribute_json_field_no_jsondata(self, json_instance):
        json_instance.jsondata = None
        json_instance.json_new = "fresh"
        assert json_instance.jsondata == {"new": "fresh"}

    def test_setattribute_regular_attr(self, json_instance):
        json_instance.regular_attr = "value"
        assert json_instance.regular_attr == "value"

    def test_get_json_data_with_data(self, json_instance):
        json_instance.jsondata = {"a": 1}
        assert json_instance.get_json_data() == {"a": 1}

    def test_get_json_data_none(self, json_instance):
        json_instance.jsondata = None
        assert json_instance.get_json_data() == {}

    def test_get_derived_object_returns_self(self, json_instance):
        assert json_instance.get_derived_object() is json_instance
        assert json_instance.get_derived_object("param") is json_instance

    def test_set_field_value_not_found(self, json_instance):
        result = json_instance.set_field_value("nonexistent", "attr", "val")
        assert result is None

    def test_get_form_with_text_source(self, json_instance):
        view = MagicMock()
        view.get_form.return_value = "expected_form"
        json_instance.get_form_source = MagicMock(return_value="Name::****")

        with patch("pytigon_lib.schdjangoext.models.form_from_str") as mock_ffs:
            mock_ffs.return_value = MagicMock()
            result = json_instance.get_form(view, MagicMock(), forms.Form)
            view.get_form.assert_called_once()
            assert result == "expected_form"

    def test_get_form_with_form_source_none(self, json_instance):
        view = MagicMock()
        view.get_form.return_value = "expected_form"
        json_instance.get_form_source = MagicMock(return_value=None)
        json_instance.jsondata = {}

        result = json_instance.get_form(view, MagicMock(), forms.Form)
        view.get_form.assert_called_once()
        assert result == "expected_form"

    def test_get_form_no_source_with_data(self, json_instance):
        view = MagicMock()
        view.get_form.return_value = "expected_form"
        json_instance.jsondata = {"field1": "val1"}
        del json_instance.get_form_source

        result = json_instance.get_form(view, MagicMock(), forms.Form)
        view.get_form.assert_called_once()
        assert result == "expected_form"

    def test_get_form_no_source_no_data(self, json_instance):
        view = MagicMock()
        view.get_form.return_value = "expected_form"
        json_instance.jsondata = {}
        del json_instance.get_form_source

        result = json_instance.get_form(view, MagicMock(), forms.Form)
        view.get_form.assert_called_once()
        assert result == "expected_form"


class TestTreeModel:
    def test_tree_model_inherits_json_model(self):
        assert issubclass(TreeModel, JSONModel)

    def test_tree_model_is_abstract(self):
        assert TreeModel._meta.abstract is True


class TestAssociatedModel:
    def test_application_field_config(self):
        field = AssociatedModel._meta.get_field("application")
        assert field.max_length == 64
        assert field.null is False

    def test_table_field_config(self):
        field = AssociatedModel._meta.get_field("table")
        assert field.max_length == 64
        assert field.default == "default"

    def test_parent_id_field_config(self):
        field = AssociatedModel._meta.get_field("parent_id")
        assert field.null is True

    def test_init_new_with_4_parts(self):
        obj = AssociatedModel()
        result = obj.init_new(MagicMock(), MagicMock(), "app__table__123__mygroup")
        assert result["application"] == "app"
        assert result["table"] == "table"
        assert result["parent_id"] == "123"
        assert result["group"] == "mygroup"

    def test_init_new_with_3_parts(self):
        obj = AssociatedModel()
        result = obj.init_new(MagicMock(), MagicMock(), "app__table__456")
        assert result["application"] == "app"
        assert result["table"] == "table"
        assert result["parent_id"] == "456"
        assert result["group"] == "default"

    def test_init_new_with_none_value(self):
        obj = AssociatedModel()
        result = obj.init_new(MagicMock(), MagicMock(), None)
        assert result["application"] == "default"
        assert result["table"] == "default"
        assert result["parent_id"] == 0
        assert result["group"] == "default"

    def test_init_new_with_invalid_value(self):
        obj = AssociatedModel()
        result = obj.init_new(MagicMock(), MagicMock(), "short")
        assert result["application"] == "default"


class TestExtendClass:
    def test_extend_class_normal_mode(self):
        class Base:
            pass

        class Main(Base):
            pass

        with patch("sys.argv", ["runserver"]):
            original_bases = Main.__bases__
            extend_class(Main, object)
            assert len(Main.__bases__) == len(original_bases) + 1

    def test_extend_class_skipped_in_migrations(self):
        class Base:
            pass

        class Main(Base):
            pass

        for cmd in ["makemigrations", "makeallmigrations", "exporttolocaldb"]:
            with patch("sys.argv", ["manage.py", cmd]):
                original_bases = Main.__bases__
                extend_class(Main, int)
                assert Main.__bases__ == original_bases


class TestOverwritableCallable:
    def test_runtime_mode_callable_and_settable(self):
        import sys

        sys.argv = ["runserver"]

        import importlib

        import pytigon_lib.schdjangoext.models as mod

        importlib.reload(mod)

        def sample():
            return "original"

        oc = mod.OverwritableCallable(sample)
        assert oc() == "original"

        def replacement():
            return "replaced"

        oc.set_function(replacement)
        assert oc() == "replaced"


class TestStandardTableAction:
    def test_empty_action_returns_none(self):
        result = standard_table_action(MagicMock(), MagicMock(), MagicMock(), {}, set())
        assert result is None

    def test_action_not_in_operations(self):
        result = standard_table_action(MagicMock(), MagicMock(), MagicMock(), {"action": "unknown"}, {"copy"})
        assert result is None

    def test_copy_with_pks(self):
        request = MagicMock()
        request.GET.get.return_value = "1,2,3"
        list_view = MagicMock()
        list_view.get_queryset.return_value = MagicMock()

        with patch("pytigon_lib.schdjangoext.models.serializers.serialize", return_value="json_data") as mock_ser:
            result = standard_table_action(MagicMock(), list_view, request, {"action": "copy"}, {"copy"})
            assert result == "json_data"
            mock_ser.assert_called_once()

    def test_copy_no_pks(self):
        request = MagicMock()
        request.GET.get.return_value = ""
        list_view = MagicMock()

        with patch("pytigon_lib.schdjangoext.models.serializers.serialize", return_value="json_data") as mock_ser:
            result = standard_table_action(MagicMock(), list_view, request, {"action": "copy"}, {"copy"})
            assert result == "json_data"

    def test_paste_action(self):
        request = MagicMock()
        list_view = MagicMock()
        list_view.kwargs = {"parent_pk": None}
        cls = MagicMock()

        result = standard_table_action(
            cls,
            list_view,
            request,
            {"action": "paste", "data": [{"fields": {"name": "test"}}]},
            {"paste"},
        )
        assert result == {"success": 1}

    def test_paste_skips_id_and_pk(self):
        request = MagicMock()
        list_view = MagicMock()
        list_view.kwargs = {"parent_pk": None}
        cls = MagicMock()
        cls.return_value = MagicMock()

        result = standard_table_action(
            cls,
            list_view,
            request,
            {"action": "paste", "data": [{"fields": {"id": 1, "pk": 2, "name": "test"}}]},
            {"paste"},
        )
        assert result == {"success": 1}

    def test_paste_with_parent_pk(self):
        request = MagicMock()
        list_view = MagicMock()
        list_view.kwargs = {"parent_pk": 42}
        cls = MagicMock()
        obj_mock = MagicMock()
        cls.return_value = obj_mock

        result = standard_table_action(
            cls,
            list_view,
            request,
            {"action": "paste", "data": [{"fields": {"parent": 1, "name": "child"}}]},
            {"paste"},
        )
        assert result == {"success": 1}
        assert obj_mock.parent_id == 42

    def test_delete_with_pks(self):
        request = MagicMock()
        request.GET.get.return_value = "1,2,3"
        list_view = MagicMock()

        result = standard_table_action(
            MagicMock(), list_view, request, {"action": "delete"}, {"delete"}
        )
        assert result == []

    def test_delete_no_pks(self):
        request = MagicMock()
        request.GET.get.return_value = ""
        list_view = MagicMock()

        result = standard_table_action(
            MagicMock(), list_view, request, {"action": "delete"}, {"delete"}
        )
        assert result == []


class TestGetForm:
    def test_get_form_with_fields(self):
        class FakeModel(models.Model):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "test_modelform"

        obj = FakeModel()
        form_cls = get_form(obj, fields_list=["name"])
        assert issubclass(form_cls, forms.ModelForm)
        assert form_cls.Meta.model is FakeModel
        assert form_cls.Meta.fields == ["name"]

    def test_get_form_all_fields(self):
        class FakeModel(models.Model):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "test_modelform2"

        obj = FakeModel()
        form_cls = get_form(obj)
        assert issubclass(form_cls, forms.ModelForm)
        assert form_cls.Meta.fields == "__all__"

    def test_get_form_with_widgets(self):
        class FakeModel(models.Model):
            name = models.CharField(max_length=100)

            class Meta:
                app_label = "test_modelform3"

        obj = FakeModel()
        widgets = {"name": forms.TextInput(attrs={"class": "custom"})}
        form_cls = get_form(obj, widgets_dict=widgets)
        assert form_cls.Meta.widgets == widgets


class TestAdminRegister:
    def test_admin_register_not_in_installed_apps(self):
        with patch("django.conf.settings.INSTALLED_APPS", []):
            result = admin_register(MagicMock())
            assert result is None


class TestAssociatedJSONModel:
    def test_inherits_both_parents(self):
        from pytigon_lib.schdjangoext.models import AssociatedJSONModel

        assert issubclass(AssociatedJSONModel, AssociatedModel)
        assert issubclass(AssociatedJSONModel, JSONModel)
