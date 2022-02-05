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
# copyright: "Copyright (C) ????/2020 Slawomir Cholaj"
# license: "LGPL 3.0"
# version: "0.108"

from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType


def add_graphql_to_class(model, filter_fields, query_class):
    _model = model
    _filter_fields = filter_fields

    if hasattr(_model._meta, "app_label"):
        app_label = getattr(_model._meta, "app_label")
    else:
        app_label = ""

    # class __Model(DjangoObjectType):
    class Meta:
        nonlocal _model, _filter_fields
        model = _model
        interfaces = (Node,)
        filter_fields = _filter_fields

    _Model = type(
        app_label + "__" + _model.__name__ + "__class",
        (DjangoObjectType,),
        {"Meta": Meta},
    )

    setattr(query_class, app_label + "__" + _model.__name__, Node.Field(_Model))
    setattr(
        query_class,
        app_label + "__" + _model.__name__ + "All",
        DjangoFilterConnectionField(_Model),
    )
