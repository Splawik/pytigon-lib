from unittest.mock import MagicMock, patch

import pytest
from django import forms

from pytigon_lib.schdjangoext.formfields import (
    HeavySelect2Field,
    HeavySelect2MultipleField,
    ModelChoiceFieldWithIcon,
    ModelMultipleChoiceFieldWithIcon,
    ModelSelect2Field,
    ModelSelect2MultipleField,
    Select2Field,
    Select2MultipleField,
)
from pytigon_lib.schdjangoext.formwidgets import (
    CheckboxSelectMultipleWithIcon,
    RadioSelectWithIcon,
)


class TestModelChoiceFieldWithIcon:
    def test_widget_is_radio_select_with_icon(self):
        field = ModelChoiceFieldWithIcon(queryset=MagicMock())
        assert field.widget.__class__ is RadioSelectWithIcon


class TestModelMultipleChoiceFieldWithIcon:
    def test_widget_is_checkbox_select_multiple_with_icon(self):
        field = ModelMultipleChoiceFieldWithIcon(queryset=MagicMock())
        assert field.widget.__class__ is CheckboxSelectMultipleWithIcon


class TestSelect2Field:
    def test_init_basic(self):
        choices = [("a", "A"), ("b", "B")]
        field = Select2Field(choices=choices)
        assert isinstance(field, forms.ChoiceField)
        assert field.widget.attrs["data-minimum-input-length"] == 0

    def test_init_with_custom_attrs(self):
        field = Select2Field(choices=(), attrs={"class": "my-class"})
        assert field.widget.attrs["class"] == "my-class"

    def test_init_preserves_minimum_input_length(self):
        field = Select2Field(choices=(), attrs={"data-minimum-input-length": 5})
        assert field.widget.attrs["data-minimum-input-length"] == 5


class TestSelect2MultipleField:
    def test_init_basic(self):
        choices = [("x", "X"), ("y", "Y")]
        field = Select2MultipleField(choices=choices)
        assert isinstance(field, forms.MultipleChoiceField)
        assert field.widget.attrs["data-minimum-input-length"] == 0

    def test_init_with_attrs(self):
        field = Select2MultipleField(choices=(), attrs={"style": "width:100%"})
        assert field.widget.attrs["style"] == "width:100%"


class TestHeavySelect2Field:
    def test_init_basic(self):
        field = HeavySelect2Field(data_url="/api/search/")
        assert isinstance(field, forms.ChoiceField)
        assert field.widget.data_url == "/api/search/"

    def test_init_with_attrs(self):
        field = HeavySelect2Field(data_url="/api/", attrs={"class": "heavy"})
        assert field.widget.attrs["class"] == "heavy"


class TestHeavySelect2MultipleField:
    def test_init_basic(self):
        field = HeavySelect2MultipleField(data_url="/api/multi/")
        assert isinstance(field, forms.MultipleChoiceField)
        assert field.widget.data_url == "/api/multi/"

    def test_init_with_custom_minimum_length(self):
        field = HeavySelect2MultipleField(data_url="/api/", attrs={"data-minimum-input-length": 3})
        assert field.widget.attrs["data-minimum-input-length"] == 3


class TestModelSelect2Field:
    def test_init_with_model(self):
        field = ModelSelect2Field(model=MagicMock(), queryset=MagicMock(), search_fields=["name"])
        assert isinstance(field, forms.ModelChoiceField)
        assert field.widget.attrs.get("style") == "width:100%;"

    def test_init_default_minimum_length(self):
        field = ModelSelect2Field(queryset=MagicMock(), search_fields=[])
        assert field.widget.attrs["data-minimum-input-length"] == 0


class TestModelSelect2MultipleField:
    def test_init_basic(self):
        field = ModelSelect2MultipleField(model=MagicMock(), queryset=MagicMock(), search_fields=["title"])
        assert isinstance(field, forms.ModelMultipleChoiceField)

    def test_init_default_attrs(self):
        field = ModelSelect2MultipleField(queryset=MagicMock(), search_fields=[])
        assert field.widget.attrs["data-minimum-input-length"] == 0
