from django import forms
from pytigon_lib.schdjangoext.formwidgets import (
    CheckboxSelectMultipleWithIcon,
    RadioSelectWithIcon,
)
from django_select2.forms import (
    Select2Widget,
    Select2MultipleWidget,
    HeavySelect2Widget,
    HeavySelect2MultipleWidget,
    ModelSelect2Widget,
    ModelSelect2MultipleWidget,
)


class ModelChoiceFieldWithIcon(forms.ModelChoiceField):
    """Extended version of django django models.ManyToManyField.
    If label contains contains '|' its value split to two parts. First part should be image address, second
    part should be a label.
    """

    widget = RadioSelectWithIcon


class ModelMultipleChoiceFieldWithIcon(forms.ModelMultipleChoiceField):
    widget = CheckboxSelectMultipleWithIcon


class Select2Field(forms.ChoiceField):
    def __init__(self, choices=(), attrs={}, **kwargs):
        widget = Select2Widget(attrs=attrs, choices=choices)
        super().__init__(choices=choices, widget=widget, **kwargs)


class Select2MultipleField(forms.MultipleChoiceField):
    def __init__(self, choices=(), attrs={}, **kwargs):
        widget = Select2MultipleWidget(attrs=attrs, choices=choices)
        super().__init__(choices=choices, widget=widget, **kwargs)


class HeavySelect2Field(forms.ChoiceField):
    def __init__(self, data_url, attrs={}, **kwargs):
        widget = HeavySelect2Widget(data_url=data_url, attrs=attrs)
        super().__init__(widget=widget, **kwargs)


class HeavySelect2MultipleField(forms.MultipleChoiceField):
    def __init__(self, data_url, attrs={}, **kwargs):
        widget = HeavySelect2MultipleWidget(data_url=data_url, attrs=attrs)
        super().__init__(widget=widget, **kwargs)


class ModelSelect2Field(forms.ChoiceField):
    def __init__(
        self,
        model=None,
        queryset=None,
        search_fields=None,
        attrs={},
        empty_label="-----",
        **kwargs
    ):
        widget = ModelSelect2Widget(
            model=model,
            queryset=queryset,
            search_fields=search_fields,
            empty_label=empty_label,
            attrs=attrs,
        )
        super().__init__(widget=widget, **kwargs)


class ModelSelect2MultipleField(forms.MultipleChoiceField):
    def __init__(
        self,
        model=None,
        queryset=None,
        search_fields=None,
        attrs={},
        empty_label="-----",
        **kwargs
    ):
        widget = ModelSelect2MultipleWidget(
            model=model,
            queryset=queryset,
            search_fields=search_fields,
            empty_label=empty_label,
            attrs=attrs,
        )
        super().__init__(widget=widget, **kwargs)
