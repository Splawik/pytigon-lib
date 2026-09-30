"""Module contains many additional fields for django models."""

# from itertools import chain

import warnings

from django import forms
from django.db import models
from django.forms.widgets import HiddenInput
from django_select2.forms import ModelSelect2MultipleWidget, ModelSelect2Widget

from pytigon_lib.schdjangoext.formfields import (
    ModelChoiceFieldWithIcon,
    ModelMultipleChoiceFieldWithIcon,
)
from pytigon_lib.schdjangoext.tools import make_href


class ModelSelect2WidgetExt(ModelSelect2Widget):
    """Extended Select2 widget with dynamic form-open and add-form buttons.

    Supports ``href1`` for opening a related form and ``href2`` for
    adding a new object directly from the select widget.
    """

    input_type = "select2"

    def __init__(self, href1=None, href2=None, label="", minimum_input_length=0, **argv):
        """Initialize the widget with optional href attributes for related actions.

        Args:
            href1: URL for opening a related form (adds 'show-form-btn' CSS class).
            href2: URL for adding a new related object.
            label: Widget label.
            minimum_input_length: Minimum input length before search triggers.
            **argv: Additional keyword arguments forwarded to ModelSelect2Widget.
        """
        # Ensure attrs dict exists and set base attributes
        attrs = argv.setdefault("attrs", {})
        if href1:
            attrs["href1"] = href1
        if href2:
            attrs["href2"] = href2
        attrs["data-minimum-input-length"] = minimum_input_length
        attrs["class"] = "form-control" + (" show-form-btn" if href1 else "")
        ModelSelect2Widget.__init__(self, label=label, **argv)


class ModelSelect2MultipleWidgetExt(ModelSelect2MultipleWidget):
    """Extended Select2 multiple-select widget with streamlined initialization."""

    input_type = "select2"

    def __init__(self, label="", minimum_input_length=0, **argv):
        """Initialize the multi-select widget.

        Args:
            label: Widget label.
            minimum_input_length: Minimum input length before search.
            **argv: Additional keyword arguments forwarded to parent.
        """
        attrs = argv.setdefault("attrs", {})
        attrs["data-minimum-input-length"] = minimum_input_length
        attrs["class"] = "form-control"
        ModelSelect2MultipleWidget.__init__(self, label=label, **argv)


# Keyword arguments shared by ForeignKey and ManyToManyField extensions,
# popped from kwargs before forwarding to the Django base class.
_FIELD_KWARGS = {
    "search_fields": None,
    "query": None,
    "filter": "-",
    "show_form": True,
    "can_add": False,
    "select2": False,
    "minimum_input_length": 0,
    "app_template": "",
}


def _extract_field_kwargs(kwargs):
    """Pop and return the shared extension keyword arguments from *kwargs*."""
    extracted = {}
    for key, default in _FIELD_KWARGS.items():
        extracted[key] = kwargs.pop(key, default)
    return extracted


#: Cache of generated form classes, keyed by
#: ``(field, search_fields, query, minimum_input_length, href1, href2)``.
#: Building a fresh class per formfield() call defeats Django's form-class
#: caching and multiplies the Media objects it collects.
_FORM_CLASS_CACHE: dict = {}


def _build_choice_form_class(href1, href2, verbose_name, search_fields, query, minimum_input_length):
    """Build (and memoize) the ModelChoiceField subclass for this field."""

    class _Field(forms.ModelChoiceField):
        def __init__(self, queryset, *argi, **argv):
            nonlocal query, search_fields, minimum_input_length
            if query:
                if "Q" in query:
                    queryset = queryset.filter(query["Q"])
                if "order" in query:
                    queryset = queryset.order_by(*query["order"])
                if "limit" in query:
                    queryset = queryset[: query["limit"]]

            if search_fields:
                widget = ModelSelect2WidgetExt(
                    href1,
                    href2,
                    verbose_name,
                    queryset=queryset,
                    search_fields=search_fields,
                    minimum_input_length=minimum_input_length,
                )
                widget.attrs["style"] = "width:100%;"
                argv["widget"] = widget
            forms.ModelChoiceField.__init__(self, queryset, *argi, **argv)

    return _Field


class ForeignKey(models.ForeignKey):
    """Extended version of django models.ForeignKey class. Class allows you to add new objects and
    selecting existing objects in better way.
    """

    def __init__(self, *args, **kwargs):
        kw = _extract_field_kwargs(kwargs)
        self.__dict__.update(kw)

        super().__init__(*args, **kwargs)

        if len(args) > 0:
            self.to = args[0]

    def formfield(self, **kwargs):
        """Return a form field for this ForeignKey with Select2 widget support.

        Builds href1 (form popup) and href2 (add popup) URLs and
        optionally wraps the field in a custom ModelChoiceField that
        uses Select2 for search_fields or query-based filtering.
        """
        if isinstance(self.to, str):
            to = self.model
        else:
            to = self.to

        if self.show_form:
            href1 = make_href(
                "/{}/table/{}/{}/form{}/get/".format(
                    to._meta.app_label,
                    to._meta.object_name,
                    self.filter,
                    "__" + self.app_template if self.app_template else "",
                )
            )
        else:
            href1 = None
        if self.can_add:
            href2 = make_href(
                f"/{to._meta.app_label}/table/{to._meta.object_name}/{self.filter}/add/"
            )
        else:
            href2 = None

        if self.search_fields or self.query:  # or self.select2:
            # One form class per (field, search/query configuration). Building
            # it per formfield() call defeats Django's form-class caching and
            # multiplies the Media objects it collects.
            cache_key = (
                self,
                tuple(self.search_fields) if self.search_fields else None,
                repr(self.query),
                self.minimum_input_length,
                href1,
                href2,
            )
            form_class = _FORM_CLASS_CACHE.get(cache_key)
            if form_class is None:
                form_class = _build_choice_form_class(
                    href1,
                    href2,
                    self.verbose_name,
                    self.search_fields,
                    self.query,
                    self.minimum_input_length,
                )
                _FORM_CLASS_CACHE[cache_key] = form_class

            defaults = {
                "form_class": form_class,
            }
        else:
            defaults = {}
        defaults.update(**kwargs)
        return super().formfield(**defaults)

    def set(self, parameters):
        for key, value in parameters.items():
            setattr(self, key, value)


class ManyToManyField(models.ManyToManyField):
    """Extended version of django models.ForeignKey class. Class allows you to add new objects and
    selecting existing objects in better way.
    """

    def __init__(self, *args, **kwargs):
        kw = _extract_field_kwargs(kwargs)
        self.__dict__.update(kw)

        # A ManyToManyField has no notion of NULL: the relation is a join
        # table. Silently dropping the arguments hides a real modelling
        # mistake, so say so instead.
        for key in ("null", "blank"):
            if key in kwargs:
                value = kwargs.pop(key)
                if value:
                    warnings.warn(
                        f"ManyToManyField does not support {key}=True; the argument "
                        f"is ignored (requested value: {value!r}).",
                        RuntimeWarning,
                        stacklevel=2,
                    )

        super().__init__(*args, **kwargs)

        if len(args) > 0:
            self.to = args[0]

    def formfield(self, **kwargs):
        """Return a form field for this ManyToManyField with Select2 widget support.

        When search_fields or query are provided, wraps the field in a
        custom ModelMultipleChoiceField that uses Select2 for filtering.
        """
        field = self

        if self.search_fields or self.query:
            _search_fields = self.search_fields
            _query = self.query
            _minimum_input_length = self.minimum_input_length

            class _Field(forms.ModelMultipleChoiceField):
                def __init__(self, queryset, *argi, **argv):
                    nonlocal _query, _search_fields, _minimum_input_length
                    if _query:
                        if "Q" in _query:
                            queryset = queryset.filter(_query["Q"])
                        if "order" in _query:
                            queryset = queryset.order_by(*_query["order"])
                        if "limit" in _query:
                            queryset = queryset[: _query["limit"]]

                    if _search_fields:
                        widget = ModelSelect2MultipleWidgetExt(
                            label=field.verbose_name,
                            queryset=queryset,
                            search_fields=_search_fields,
                            minimum_input_length=_minimum_input_length,
                        )
                        widget.attrs["style"] = "width:100%;"
                        argv["widget"] = widget

                    forms.ModelMultipleChoiceField.__init__(self, queryset, *argi, **argv)

            defaults = {
                "form_class": _Field,
            }
        else:
            defaults = {}
        defaults.update(**kwargs)
        return super().formfield(**defaults)

    def set(self, parameters):
        for key, value in parameters.items():
            setattr(self, key, value)


class HiddenForeignKey(models.ForeignKey):
    """Version of django models.ForeignKey class with hidden widget."""

    def __init__(self, *argi, **argv):
        argv.pop("select2", None)
        super().__init__(*argi, **argv)

    def formfield(self, **kwargs):
        field = models.ForeignKey.formfield(self, **kwargs)
        field.widget = HiddenInput()
        field.widget.choices = None
        return field


class ManyToManyFieldWithIcon(models.ManyToManyField):
    """Extended version of django django models.ManyToManyField.
    If label contains contains '|' its value split to two parts. First part should be image address, second
    part should be a label.
    """

    def formfield(self, **kwargs):
        if kwargs:
            kwargs["form_class"] = ModelMultipleChoiceFieldWithIcon
        else:
            kwargs = {"form_class": ModelMultipleChoiceFieldWithIcon}
        return super().formfield(**kwargs)


class ForeignKeyWithIcon(models.ForeignKey):
    """Extended version of django django models.ForeignKey.
    If label contains contains '|' its value split to two parts. First part should be image address, second
    part should be a label.
    """

    def formfield(self, **kwargs):
        if kwargs:
            kwargs["form_class"] = ModelChoiceFieldWithIcon
        else:
            kwargs = {"form_class": ModelChoiceFieldWithIcon}
        return super().formfield(**kwargs)


class NullBooleanField(models.BooleanField):
    def __init__(self, *args, **kwargs):
        kwargs["null"] = True
        super().__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {
            "form_class": forms.BooleanField,
        }
        defaults.update(kwargs)
        return super().formfield(**defaults)


class TreeForeignKey(ForeignKey):
    pass


PtigForeignKey = ForeignKey
PtigManyToManyField = ManyToManyField
PtigHiddenForeignKey = HiddenForeignKey
PtigForeignKeyWithIcon = ForeignKeyWithIcon
PtigManyToManyFieldWithIcon = ManyToManyFieldWithIcon
PtigTreeForeignKey = TreeForeignKey
