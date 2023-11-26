#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

# Pytigon - wxpython and django application framework

# author: "Slawomir Cholaj (slawomir.cholaj@gmail.com)"
# copyright: "Copyright (C) ????/2012 Slawomir Cholaj"
# license: "LGPL 3.0"
# version: "0.1a"


"""Module contains many additional fields for django models.
"""

# from itertools import chain

from django.utils.translation import gettext_lazy as _
from django.db import models
from django import forms
from django_select2.forms import ModelSelect2Widget, ModelSelect2MultipleWidget
from django.forms.widgets import HiddenInput

from pytigon_lib.schdjangoext.tools import make_href
from pytigon_lib.schdjangoext.formfields import (
    ModelMultipleChoiceFieldWithIcon,
    ModelChoiceFieldWithIcon,
)


class ModelSelect2WidgetExt(ModelSelect2Widget):
    input_type = "select2"

    def __init__(
        self, href1=None, href2=None, label="", minimum_input_length=0, **argv
    ):
        if href1:
            if "attrs" in argv:
                argv["attrs"]["href1"] = href1
            else:
                argv["attrs"] = {"href1": href1}
        if href2:
            if "attrs" in argv:
                argv["attrs"]["href2"] = href2
            else:
                argv["attrs"] = {"href2": href2}
        if "attrs" in argv:
            argv["attrs"]["data-minimum-input-length"] = minimum_input_length
            argv["attrs"]["class"] = "form-control" + (" show-form-btn" if href1 else "")
        else:
            argv["attrs"] = {"data-minimum-input-length": minimum_input_length}
            argv["attrs"]["class"] = "form-control" + (" show-form-btn" if href1 else "")
        ModelSelect2Widget.__init__(self, label=label, **argv)


class ModelSelect2MultipleWidgetExt(ModelSelect2MultipleWidget):
    def __init__(self, label="", minimum_input_length=0, **argv):
        if "attrs" in argv:
            argv["attrs"]["data-minimum-input-length"] = minimum_input_length
            argv["attrs"]["class"] = "form-control"
        else:
            argv["attrs"] = {"data-minimum-input-length": minimum_input_length}
            argv["attrs"]["class"] = "form-control"
        ModelSelect2MultipleWidget.__init__(self, label=label, **argv)

    input_type = "select2"


class ForeignKey(models.ForeignKey):
    """Extended version of django models.ForeignKey class. Class allows you to add new objects and
    selecting existing objects in better way.
    """

    def __init__(self, *args, **kwargs):
        if "search_fields" in kwargs:
            self.search_fields = kwargs["search_fields"]
            del kwargs["search_fields"]
        else:
            self.search_fields = None
        if "filter" in kwargs:
            self.filter = kwargs["filter"]
            del kwargs["filter"]
        else:
            self.filter = "-"
        if "query" in kwargs:
            self.query = kwargs["query"]
            del kwargs["query"]
        else:
            self.query = None
        if "show_form" in kwargs:
            self.show_form = kwargs["show_form"]
            del kwargs["show_form"]
        else:
            self.show_form = True
        if "can_add" in kwargs:
            self.can_add = kwargs["can_add"]
            del kwargs["can_add"]
        else:
            self.can_add = False
        if "select2" in kwargs:
            self.select2 = True
            del kwargs["select2"]
        else:
            self.select2 = False

        if "minimum_input_length" in kwargs:
            self.minimum_input_length = kwargs["minimum_input_length"]
            del kwargs["minimum_input_length"]
        else:
            self.minimum_input_length = 0
        if "app_template" in kwargs:
            self.app_template = kwargs["app_template"]
            del kwargs["app_template"]
        else:
            self.app_template = ""

        super().__init__(*args, **kwargs)

        if len(args) > 0:
            self.to = args[0]

    def formfield(self, **kwargs):
        if type(self.to) == str:
            to = self.model
        else:
            to = self.to

        if self.show_form:
            href1 = make_href(
                "/%s/table/%s/%s/form%s/get/"
                % (
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
                "/%s/table/%s/%s/add/"
                % (to._meta.app_label, to._meta.object_name, self.filter)
            )
        else:
            href2 = False

        field = self

        if self.search_fields or self.query: # or self.select2:
            _search_fields = self.search_fields
            _query = self.query
            _minimum_input_length = self.minimum_input_length

            class _Field(forms.ModelChoiceField):
                def __init__(self, queryset, *argi, **argv):
                    nonlocal _query, _search_fields, _minimum_input_length
                    if _query:
                        if "Q" in _query:
                            queryset = queryset.filter(_query["Q"])
                        if "order" in _query:
                            queryset = queryset.order_by(*_query["order"])
                        if "limmit" in _query:
                            queryset = queryset[: _query["limit"]]

                    if _search_fields:
                        widget = ModelSelect2WidgetExt(
                            href1,
                            href2,
                            field.verbose_name,
                            queryset=queryset,
                            search_fields=_search_fields,
                            minimum_input_length=_minimum_input_length,
                        )
                        widget.attrs["style"] = "width:100%;"
                        argv["widget"] = widget
                    forms.ModelChoiceField.__init__(self, queryset, *argi, **argv)

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


class ManyToManyField(models.ManyToManyField):
    """Extended version of django models.ForeignKey class. Class allows you to add new objects and
    selecting existing objects in better way.
    """

    def __init__(self, *args, **kwargs):
        if "search_fields" in kwargs:
            self.search_fields = kwargs["search_fields"]
            del kwargs["search_fields"]
        else:
            self.search_fields = None
        if "query" in kwargs:
            self.query = kwargs["query"]
            del kwargs["query"]
        else:
            self.query = None
        if "filter" in kwargs:
            self.filter = kwargs["filter"]
            del kwargs["filter"]
        else:
            self.filter = "-"
        if "minimum_input_length" in kwargs:
            self.minimum_input_length = kwargs["minimum_input_length"]
            del kwargs["minimum_input_length"]
        else:
            self.minimum_input_length = 0
        if "app_template" in kwargs:
            self.app_template = kwargs["app_template"]
            del kwargs["app_template"]
        else:
            self.app_template = ""

        super().__init__(*args, **kwargs)

        if len(args) > 0:
            self.to = args[0]

    def formfield(self, **kwargs):
        if type(self.to) == str:
            to = self.model
        else:
            to = self.to

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
                        if "limmit" in _query:
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

                    forms.ModelMultipleChoiceField.__init__(
                        self, queryset, *argi, **argv
                    )

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
        if 'select2' in argv:
            del argv['select2']
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
        db = kwargs.pop("using", None)
        defaults = {
            "form_class": ModelChoiceFieldWithIcon,
            "queryset": self.rel.to._default_manager.using(db).complex_filter(
                self.rel.limit_choices_to
            ),
            "to_field_name": self.rel.field_name,
        }
        defaults.update(kwargs)
        return super(models.ForeignKey, self).formfield(**defaults)


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
