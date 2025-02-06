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
    """Extended version of django's ModelChoiceField.
    If the label contains '|', it splits into two parts: the first part is the image address,
    and the second part is the label.
    """

    widget = RadioSelectWithIcon


class ModelMultipleChoiceFieldWithIcon(forms.ModelMultipleChoiceField):
    """Extended version of django's ModelMultipleChoiceField with icon support."""

    widget = CheckboxSelectMultipleWithIcon


class Select2Field(forms.ChoiceField):
    """A ChoiceField that uses Select2Widget for better UI."""

    def __init__(self, choices=(), attrs=None, **kwargs):
        attrs = attrs or {}
        attrs.setdefault("data-minimum-input-length", 0)
        widget = Select2Widget(attrs=attrs, choices=choices)
        super().__init__(choices=choices, widget=widget, **kwargs)


class Select2MultipleField(forms.MultipleChoiceField):
    """A MultipleChoiceField that uses Select2MultipleWidget for better UI."""

    def __init__(self, choices=(), attrs=None, **kwargs):
        attrs = attrs or {}
        attrs.setdefault("data-minimum-input-length", 0)
        widget = Select2MultipleWidget(attrs=attrs, choices=choices)
        super().__init__(choices=choices, widget=widget, **kwargs)


class HeavySelect2Field(forms.ChoiceField):
    """A ChoiceField that uses HeavySelect2Widget for AJAX-based options."""

    def __init__(self, data_url, attrs=None, **kwargs):
        attrs = attrs or {}
        attrs.setdefault("data-minimum-input-length", 0)
        widget = HeavySelect2Widget(data_url=data_url, attrs=attrs)
        super().__init__(widget=widget, **kwargs)


class HeavySelect2MultipleField(forms.MultipleChoiceField):
    """A MultipleChoiceField that uses HeavySelect2MultipleWidget for AJAX-based options."""

    def __init__(self, data_url, attrs=None, **kwargs):
        attrs = attrs or {}
        attrs.setdefault("data-minimum-input-length", 0)
        widget = HeavySelect2MultipleWidget(data_url=data_url, attrs=attrs)
        super().__init__(widget=widget, **kwargs)


class ModelSelect2Field(forms.ModelChoiceField):
    """A ModelChoiceField that uses ModelSelect2Widget for AJAX-based model choices."""

    def __init__(
        self,
        model=None,
        queryset=None,
        search_fields=None,
        attrs=None,
        empty_label="-----",
        **kwargs
    ):
        attrs = attrs or {}
        attrs.setdefault("data-minimum-input-length", 0)
        widget = ModelSelect2Widget(
            model=model,
            queryset=queryset,
            search_fields=search_fields,
            empty_label=empty_label,
            attrs=attrs,
        )
        widget.attrs["style"] = "width:100%;"
        super().__init__(widget=widget, queryset=queryset, **kwargs)


class ModelSelect2MultipleField(forms.ModelMultipleChoiceField):
    """A ModelMultipleChoiceField that uses ModelSelect2MultipleWidget for AJAX-based model choices."""

    def __init__(
        self,
        model=None,
        queryset=None,
        search_fields=None,
        attrs=None,
        empty_label="-----",
        **kwargs
    ):
        attrs = attrs or {}
        attrs.setdefault("data-minimum-input-length", 0)
        widget = ModelSelect2MultipleWidget(
            model=model,
            queryset=queryset,
            search_fields=search_fields,
            empty_label=empty_label,
            attrs=attrs,
        )
        super().__init__(widget=widget, queryset=queryset, **kwargs)
