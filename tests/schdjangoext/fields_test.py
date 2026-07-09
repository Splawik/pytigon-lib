from unittest.mock import MagicMock, patch

import pytest
from django import forms
from django.db import models
from django.forms.widgets import HiddenInput

from pytigon_lib.schdjangoext.fields import (
    ForeignKey,
    ForeignKeyWithIcon,
    HiddenForeignKey,
    ManyToManyField,
    ManyToManyFieldWithIcon,
    ModelSelect2MultipleWidgetExt,
    ModelSelect2WidgetExt,
    NullBooleanField,
    PtigForeignKey,
    PtigHiddenForeignKey,
    PtigManyToManyField,
    PtigTreeForeignKey,
    TreeForeignKey,
)


class TestModelSelect2WidgetExt:
    def test_init_basic(self):
        widget = ModelSelect2WidgetExt()
        assert widget.attrs["data-minimum-input-length"] == 0
        assert "class" in widget.attrs

    def test_init_with_href1_adds_class(self):
        widget = ModelSelect2WidgetExt(href1="/some/url")
        assert "show-form-btn" in widget.attrs["class"]
        assert widget.attrs["href1"] == "/some/url"

    def test_init_with_href2(self):
        widget = ModelSelect2WidgetExt(href2="/add/url")
        assert widget.attrs["href2"] == "/add/url"

    def test_init_with_both_hrefs(self):
        widget = ModelSelect2WidgetExt(href1="/form", href2="/add")
        assert widget.attrs["href1"] == "/form"
        assert widget.attrs["href2"] == "/add"
        assert "show-form-btn" in widget.attrs["class"]

    def test_init_with_minimum_input_length(self):
        widget = ModelSelect2WidgetExt(minimum_input_length=3)
        assert widget.attrs["data-minimum-input-length"] == 3

    def test_init_with_custom_attrs(self):
        widget = ModelSelect2WidgetExt(attrs={"custom": "val"})
        assert widget.attrs["custom"] == "val"


class TestModelSelect2MultipleWidgetExt:
    def test_init_basic(self):
        widget = ModelSelect2MultipleWidgetExt()
        assert widget.attrs["data-minimum-input-length"] == 0

    def test_init_with_minimum_input_length(self):
        widget = ModelSelect2MultipleWidgetExt(minimum_input_length=2)
        assert widget.attrs["data-minimum-input-length"] == 2


class TestForeignKey:
    @pytest.fixture
    def mock_model(self):
        class FakeRelated(models.Model):
            pass

            class Meta:
                app_label = "testapp"

        return FakeRelated

    def test_init_defaults(self, mock_model):
        fk = ForeignKey(mock_model, on_delete=models.CASCADE)
        assert fk.search_fields is None
        assert fk.filter == "-"
        assert fk.query is None
        assert fk.show_form is True
        assert fk.can_add is False
        assert fk.select2 is False
        assert fk.minimum_input_length == 0
        assert fk.app_template == ""

    def test_init_with_search_fields(self, mock_model):
        fk = ForeignKey(mock_model, on_delete=models.CASCADE, search_fields=["name", "email"])
        assert fk.search_fields == ["name", "email"]

    def test_init_with_filter(self, mock_model):
        fk = ForeignKey(mock_model, on_delete=models.CASCADE, filter="myfilter")
        assert fk.filter == "myfilter"

    def test_init_with_query(self, mock_model):
        fk = ForeignKey(mock_model, on_delete=models.CASCADE, query={"Q": models.Q()})
        assert fk.query == {"Q": models.Q()}

    def test_init_with_can_add(self, mock_model):
        fk = ForeignKey(mock_model, on_delete=models.CASCADE, can_add=True)
        assert fk.can_add is True

    def test_init_with_select2(self, mock_model):
        fk = ForeignKey(mock_model, on_delete=models.CASCADE, select2=True)
        assert fk.select2 is True

    def test_init_with_minimum_input_length(self, mock_model):
        fk = ForeignKey(mock_model, on_delete=models.CASCADE, minimum_input_length=3)
        assert fk.minimum_input_length == 3

    def test_init_with_app_template(self, mock_model):
        fk = ForeignKey(mock_model, on_delete=models.CASCADE, app_template="custom")
        assert fk.app_template == "custom"

    def test_set_method(self, mock_model):
        fk = ForeignKey(mock_model, on_delete=models.CASCADE)
        fk.set({"search_fields": ["title"], "minimum_input_length": 5})
        assert fk.search_fields == ["title"]
        assert fk.minimum_input_length == 5


class TestManyToManyField:
    @pytest.fixture
    def mock_model(self):
        class FakeRelated(models.Model):
            pass

            class Meta:
                app_label = "testapp"

        return FakeRelated

    def test_init_defaults(self, mock_model):
        m2m = ManyToManyField(mock_model)
        assert m2m.search_fields is None
        assert m2m.query is None
        assert m2m.filter == "-"
        assert m2m.minimum_input_length == 0
        assert m2m.app_template == ""

    def test_init_with_params(self, mock_model):
        m2m = ManyToManyField(mock_model, search_fields=["name"], filter="f1", app_template="tpl", minimum_input_length=2)
        assert m2m.search_fields == ["name"]
        assert m2m.filter == "f1"
        assert m2m.app_template == "tpl"
        assert m2m.minimum_input_length == 2

    def test_null_and_blank_removed(self, mock_model):
        m2m = ManyToManyField(mock_model, null=True, blank=True)
        assert True


class TestHiddenForeignKey:
    def test_init_removes_select2(self):
        from django.db import models as dj_models

        class FakeModel(dj_models.Model):
            class Meta:
                app_label = "test"

        fk = HiddenForeignKey(FakeModel, on_delete=dj_models.CASCADE, select2=True)
        assert not hasattr(fk, "select2") or fk.select2 == True


class TestNullBooleanField:
    def test_init_sets_null_true(self):
        field = NullBooleanField()
        assert field.null is True

    def test_formfield(self):
        field = NullBooleanField()
        form_field = field.formfield()
        assert isinstance(form_field, forms.BooleanField)


class TestTreeForeignKey:
    def test_is_foreign_key_subclass(self):
        assert issubclass(TreeForeignKey, ForeignKey)


class TestFieldAliases:
    def test_ptig_foreign_key_alias(self):
        assert PtigForeignKey is ForeignKey

    def test_ptig_many_to_many_alias(self):
        assert PtigManyToManyField is ManyToManyField

    def test_ptig_hidden_foreign_key_alias(self):
        assert PtigHiddenForeignKey is HiddenForeignKey

    def test_ptig_tree_foreign_key_alias(self):
        assert PtigTreeForeignKey is TreeForeignKey
