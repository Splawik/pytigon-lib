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


"""Module contains many additional db models.
"""

import sys

from django.db import models
from django import forms
from django.core import serializers

from pytigon_lib.schtools.schjson import ComplexEncoder, ComplexDecoder
from pytigon_lib.schdjangoext.fastform import form_from_str


class JSONModel(models.Model):
    class Meta:
        abstract = True

    jsondata = models.JSONField(
        "Json data",
        encoder=ComplexEncoder,
        decoder=ComplexDecoder,
        null=True,
        blank=True,
        editable=False,
    )

    def __getattribute__(self, name):
        if name.startswith("json_"):
            if self.jsondata and name[5:] in self.jsondata:
                return self.jsondata[name[5:]]
            return None
        return super().__getattribute__(name)

    def __setattr__(self, name, value):
        if name.startswith("json_"):
            if self.jsondata:
                self.jsondata[name[5:]] = value
            else:
                self.jsondata = {name[5:]: value}
            return
        return super().__setattr__(name, value)

    def get_json_data(self):
        if self.jsondata:
            return self.jsondata
        else:
            return {}

    def get_form(self, view, request, form_class, adding=False):
        data = self.get_json_data()
        if hasattr(self, "get_form_source"):
            txt = self.get_form_source()
            if txt:
                if data:
                    form_class2 = form_from_str(
                        txt, init_data=data, base_form_class=form_class, prefix="json_"
                    )
                else:
                    form_class2 = form_from_str(
                        txt, init_data={}, base_form_class=form_class, prefix="json_"
                    )
                return view.get_form(form_class2)
            else:
                return view.get_form(form_class)
        elif data:

            class form_class2(form_class):
                def __init__(self, *args, **kwargs):
                    nonlocal data
                    super().__init__(*args, **kwargs)
                    for key, value in data.items():
                        self.fields["json_%s" % key] = forms.CharField(
                            label=key, initial=value
                        )

            return view.get_form(form_class2)
        return view.get_form(form_class)

    def get_derived_object(self, param=None):
        return self

    def set_field_value(self, field_name, attr_name, value):
        for f in self._meta.fields:
            if f.name == field_name:
                setattr(f, attr_name, value)
                return f
        else:
            return None


class TreeModel(JSONModel):
    class Meta:
        abstract = True


def standard_table_action(cls, list_view, request, data, operations):
    if "action" in data and data["action"] in operations:
        if data["action"] == "copy":
            if "pk" in request.GET:
                x = request.GET["pks"].split(",")
                x2 = [int(pos) for pos in x]
                return serializers.serialize(
                    "json", list_view.get_queryset().filter(pk__in=x2)
                )
            else:
                return serializers.serialize("json", list_view.get_queryset())
        if data["action"] == "paste":
            if "data" in data:
                data2 = data["data"]
                for obj in data2:
                    obj2 = cls()
                    for key, value in obj["fields"].items():
                        if not key in ("id", "pk"):
                            if key == "parent":
                                if "parent_pk" in list_view.kwargs:
                                    setattr(
                                        obj2, "parent_id", list_view.kwargs["parent_pk"]
                                    )
                            else:
                                setattr(obj2, key, value)
                    obj2.save()
            return {"success": 1}
        if data["action"] == "delete":
            if "pks" in request.GET:
                x = request.GET["pks"].split(",")
                x2 = [int(pos) for pos in x]
                if x2:
                    list_view.get_queryset().filter(pk__in=x2).delete()
                return []
    return None


def get_form(obj, fields_list=None, widgets_dict=None):
    class _Form(forms.ModelForm):
        class Meta:
            nonlocal obj, fields_list, widgets_dict
            model = obj.__class__
            if fields_list:
                fields = fields_list
            else:
                fields = "__all__"
            if widgets_dict:
                widgets = widgets_dict

    return _Form


def extend_class(main, base):
    main.__bases__ = tuple(
        [
            base,
        ]
        + list(main.__bases__)
    )


if (
    "makemigrations" in sys.argv
    or "makeallmigrations" in sys.argv
    or "exporttolocaldb" in sys.argv
):

    def OverwritableCallable(func):
        def __none__(fun):
            pass

        func.set_function = __none__

        return func


else:

    class OverwritableCallable:
        def __init__(self, func):
            self.func = func

        def __call__(self, *argi, **kwargs):
            return self.func(*argi, **kwargs)

        def set_function(self, func):
            self.func = func
