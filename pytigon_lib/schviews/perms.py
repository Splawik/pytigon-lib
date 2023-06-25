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

"""Functions to protect access to views.
"""

from django.conf import settings
from django.contrib.auth import authenticate

from pytigon_lib.schviews.viewtools import render_to_response
from pytigon_lib.schdjangoext.django_init import get_app_name


_ANONYMOUS = None


def filter_by_permissions(view, model, queryset_or_obj, request):
    if hasattr(model, "filter_by_permissions"):
        return model.filter_by_permissions(view, queryset_or_obj, request)
    else:
        return queryset_or_obj


def has_the_right(perm, model, param, request):
    if hasattr(model, "has_the_right"):
        return model.has_the_right(perm, param, request)
    else:
        return True


def get_anonymous():
    global _ANONYMOUS
    if not _ANONYMOUS:
        _ANONYMOUS = user = authenticate(
            username="AnonymousUser", password="AnonymousUser"
        )
    return _ANONYMOUS


def default_block(request):
    return render_to_response(
        "schsys/no_perm.html", context={}, request=request, status=401
    )


def make_perms_url_test_fun(app_name, fun, if_block_view=default_block):
    app = None
    appbase = None
    perms = None
    perm_for_url = None
    for _app in settings.INSTALLED_APPS:
        pos = get_app_name(_app)
        if app_name in pos:
            app = pos
            break
    if app:
        elementy = app.split(".")
        appbase = elementy[-1]
        try:
            module = __import__(elementy[0])
            module2 = getattr(module, elementy[-1])
            if module2:
                module3 = getattr(module2, "models")
                if module3:
                    perms = module3.Perms
                    if hasattr(perms, "PermsForUrl"):
                        perm_for_url = perms.PermsForUrl
        except:
            pass

    def perms_test(request, *args, **kwargs):
        if perm_for_url:
            perm = perm_for_url(request.path)
            user = request.user
            if not user.is_authenticated():
                user = get_anonymous()
                if not user:
                    user = request.user
            if not user.has_perm(appbase + "." + perm):
                return if_block_view(request)
        return fun(request, app_name, *args, **kwargs)

    return perms_test


def make_perms_test_fun(app, model, perm, fun, if_block_view=default_block):
    """Protect views by the authorization system

    Args:
        perm - name of permision
        fun - function to be protected
        if_block_view - views which should be called when access to fun is blocked. Default default_block fun is
            called.
    """

    def perms_test(request, *args, **kwargs):
        nonlocal perm, model

        app_instance = __import__(app)
        if hasattr(app_instance, "Perms") and not app_instance.Perms:
            return fun(request, *args, **kwargs)

        user = request.user
        if not user.is_authenticated:
            user = get_anonymous()
            if not user:
                user = request.user
        if not user.has_perm(perm):
            return if_block_view(request)
        if not has_the_right(perm, model, kwargs, request):
            return if_block_view(request)
        return fun(request, *args, **kwargs)

    return perms_test
