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

#Pytigon - wxpython and django application framework

#author: "Slawomir Cholaj (slawomir.cholaj@gmail.com)"
#copyright: "Copyright (C) ????/2012 Slawomir Cholaj"
#license: "LGPL 3.0"
#version: "0.1a"


"""Module contains many additional db models.
"""

import sys

from django.db import models
from django import forms
from django.core import serializers

from pytigon_lib.schtools.schjson import json_dumps, json_loads
from pytigon_lib.schdjangoext.fastform import form_from_str

_CONNECTED_MODELS = {}

def connect_models(parent, child):
    global _CONNECTED_MODELS
    if parent in _CONNECTED_MODELS:
        _CONNECTED_MODELS[parent].append(child)
    else:
        _CONNECTED_MODELS[parent] = [ child, ]


class JSONModel(models.Model):
    class Meta:
        abstract = True

    jsondata = models.TextField('Json data', null=True, blank=True, editable=False, )

    def __getattribute__(self, name):
        if name.startswith('json_'):
            if not hasattr(self, '_data'):
                if self.jsondata:
                    self._data = json_loads(self.jsondata)
                else:
                    self._data = {}
            if name[5:] in self._data:
                return self._data[name[5:]]

            return None

        return super().__getattribute__(name)

    def get_json_data(self):
        if not hasattr(self, "_data"):
            if self.jsondata:
                self._data = json_loads(self.jsondata)
            else:
                self._data = {}
        return self._data

    def get_form(self, view, request, form_class, adding=False):
        data = self.get_json_data()
        if hasattr(self, "get_form_source"):
            txt = self.get_form_source()
            if txt:
                if data:
                    form_class2 = form_from_str(txt, init_data=data, base_form_class=form_class, prefix="json_")
                else:
                    form_class2 = form_from_str(txt, init_data={}, base_form_class=form_class, prefix="json_")
                return view.get_form(form_class2)
            else:
                return view.get_form(form_class)
        elif data:
            class form_class2(form_class):
                def __init__(self, *args, **kwargs):
                    nonlocal data
                    super().__init__(*args, **kwargs)
                    for key, value in data.items():
                        self.fields['json_%s' % key] = forms.CharField(label=key, initial=value)
            return view.get_form(form_class2)
        return view.get_form(form_class)


    def get_connected_object(self):
        global _CONNECTED_MODELS
        if hasattr(self, "_connected_obj"):
            if self._connected_obj:
                return self._connected_obj

        if type(self) in _CONNECTED_MODELS:
            if len(_CONNECTED_MODELS) > 1:
                for item in _CONNECTED_MODELS[type(self)]:
                    if hasattr(item, 'connect_to_obj'):
                        self._connected_obj = item._connect_to_obj(self)
                        if self._connected_obj:
                            return self._connected_obj
            else:
                if hasattr(_CONNECTED_MODELS[type(self)], 'connect_to_obj'):
                    self._connected_obj = _CONNECTED_MODELS[type(self)].connect_to_obj(self)
                else:
                    self._connected_obj =  _CONNECTED_MODELS[type(self)]()
                    self._connected_obj.parent = self
                return self._connected_obj
        self._connected_obj = None
        return None

    def save(self, *args, **kwargs):
        if hasattr(self, '_data'):
            if 'json_update' in self._data:
                data = {}
                if self.jsondata:
                    d = json_loads(self.jsondata)
                    for key, value in d.items():
                        data[key] = value
                for key, value in self._data.items():
                    if key != 'json_update':
                        data[key] = value
                json_str = json_dumps(data)
                self._data = data
            else:
                json_str = json_dumps(self._data)
            self.jsondata = json_str

        connected_obj = self.get_connected_object()

        if connected_obj:
            connected_obj.save(*args, **kwargs)

        super().save(*args, **kwargs)

    def save_from_request(self, request, view_type, param):
        self.get_connected_object()
        tmp = self._connected_obj
        if tmp:
            class _NoSave():
                def save(self, *args, **kwargs):
                    pass
            self._connected_obj = _NoSave()
            tmp.save_from_request(request, view_type, param)
            self.save()
            self._connected_obj = tmp
        else:
            self.save()

    def get_form_class(self, view, request, create):
        connected_obj = self.get_connected_object()
        form_class = view.get_form_class()
        if connected_obj:
            if hasattr(connected_obj, 'extend_form'):
                form_class = connected_obj.extend_form(form_class)
        return form_class

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
    if 'action' in data and data['action'] in operations:
        if data['action'] == 'copy':
            if 'pk' in request.GET:
                x = request.GET['pks'].split(',')
                x2 = [int(pos) for pos in x]
                return serializers.serialize("json", list_view.get_queryset().filter(pk__in=x2))
            else:
                return serializers.serialize("json", list_view.get_queryset())
        if data['action'] == 'paste':
            if 'data' in data:
                data2 = data['data']
                for obj in data2:
                    obj2 = cls()
                    for key, value in obj['fields'].items():
                        if not key in ('id', 'pk'):
                            if key == 'parent':
                                if 'parent_pk' in list_view.kwargs:
                                    setattr(obj2, 'parent_id', list_view.kwargs['parent_pk'])
                            else:
                                setattr(obj2, key, value)
                    obj2.save()
            return {'success': 1}
        if data['action'] == 'delete':
            if 'pks' in request.GET:
                x = request.GET['pks'].split(',')
                x2 = [int(pos) for pos in x]
                if x2:
                    list_view.get_queryset().filter(pk__in=x2).delete()
                    print("DELETE: ", x2)
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
                fields = '__all__'
            if widgets_dict:
                widgets = widgets_dict
    return _Form


def extend_class(main, base):
    main.__bases__ = tuple([base, ] + list(main.__bases__))


if 'makemigrations' in sys.argv or 'makeallmigrations' in sys.argv:
    def OverwritableCallable(func):

        def __none__(fun):
            pass

        func.set_function = __none__

        return func
else:
    class OverwritableCallable():
        def __init__(self, func):
            self.func = func

        def __call__(self, *argi, **kwargs):
            return self.func(*argi, **kwargs)

        def set_function(self, func):
            self.func = func
