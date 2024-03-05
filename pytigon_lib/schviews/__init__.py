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

# author: "Sławomir Chołaj (slawomir.cholaj@gmail.com)"
# copyright: "Copyright (C) ????/2012 Sławomir Chołaj"
# license: "LGPL 3.0"
# version: "0.1a"

"""Generic templates

"""

import collections
import uuid
import datetime

from django.urls import get_script_prefix
from django.apps import apps
from django.views import generic
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect, Http404
from django.urls import reverse
from django.utils.functional import lazy
from django.conf import settings
from django.urls import path, re_path

import django.db.models
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from pytigon_lib.schviews.actions import new_row_ok, update_row_ok, delete_row_ok
from pytigon_lib.schviews.viewtools import render_to_response
from pytigon_lib.schtools.schjson import json_loads, json_dumps
from pytigon_lib.schtools.tools import is_in_cancan_rules

from .viewtools import (
    transform_template_name,
    LocalizationTemplateResponse,
    ExtTemplateResponse,
    DOC_TYPES,
)
from .form_fun import form_with_perms
from .perms import make_perms_test_fun, filter_by_permissions, default_block


# url:  /table/TableName/filter/target/list url width field:
# /table/TableName/parent_pk/field/filter/target/list

VIEWS_REGISTER = {"list": {}, "detail": {}, "edit": {}, "create": {}, "delete": {}}


def make_path(view_name, args=None):
    if settings.URL_ROOT_FOLDER:
        return settings.URL_ROOT_FOLDER + "/" + reverse(view_name, args=args)
    else:
        return reverse(view_name, args=args)


make_path_lazy = lazy(make_path, str)


def _isinstance(field, instances):
    for instance in instances:
        if isinstance(field, instance):
            return True
    return False


def convert_str_to_model_field(s, field):
    if _isinstance(field, (django.db.models.CharField, django.db.models.TextField)):
        return s
    elif _isinstance(field, (django.db.models.DateTimeField,)):
        return datetime.datetime.fromisoformat(s[:19])
    elif _isinstance(field, (django.db.models.DateField,)):
        return datetime.date.fromisoformat(s)
    elif _isinstance(field, (django.db.models.FloatField,)):
        return float(s)
    elif _isinstance(
        field,
        (
            django.db.models.IntegerField,
            django.db.models.BigAutoField,
        ),
    ):
        return int(s)
    elif _isinstance(field, (django.db.models.BooleanField,)):
        return True if s and s != "0" and s != "False" else False
    else:
        return s


def gen_tab_action(table, action, fun, extra_context=None):
    return path(
        r"table/%s/action/%s/" % (table, action),
        fun,
        extra_context,
        name="tab_action_" + table.lower() + "_" + action,
    )


def gen_tab_field_action(table, field, action, fun, extra_context=None):
    return path(
        r"table/%s/<int:parent_pk>/%s/action/%s/" % (table, field, action),
        fun,
        extra_context,
    )


def gen_row_action(table, action, fun, extra_context=None):
    return path(
        "table/%s/<int:pk>/action/%s/" % (table, action),
        fun,
        extra_context,
        name="row_action_" + table.lower() + "_" + action,
    )


def transform_extra_context(context1, context2):
    if context2:
        for key, value in context2.items():
            if isinstance(value, collections.abc.Callable):
                context1[key] = value()
            else:
                context1[key] = value
    return context1


def save(obj, request, view_type, param=None):
    if hasattr(obj, "save_from_request"):
        obj.save_from_request(request, view_type, param)
    else:
        obj.save()


def view_editor(
    request,
    pk,
    app,
    tab,
    model,
    template_name,
    field_edit_name,
    post_save_redirect,
    ext="py",
    extra_context=None,
    target=None,
    parent_pk=0,
    field_name=None,
):
    if request.POST:
        if target == "editable":
            name = request.POST["name"]
            value = request.POST["value"]
            pk = request.POST["pk"]
            obj = model.objects.get(id=pk)

            if (
                obj
                and hasattr(settings, "CANCAN")
                and is_in_cancan_rules(type(obj), request.ability.access_rules.rules)
            ):
                if not request.ability.can("editor_%s" % field_edit_name, obj):
                    return default_block(request)

            setattr(obj, field_edit_name, value)
            obj.save()
            return HttpResponse("OK")
        else:
            data = request.POST["data"]
            buf = data.replace("\r\n", "\n")
            # if type(buf)==str:
            #    buf = buf.encode('utf-8')
            obj = model.objects.get(id=pk)

            if (
                obj
                and hasattr(settings, "CANCAN")
                and is_in_cancan_rules(type(obj), request.ability.access_rules.rules)
            ):
                if not request.ability.can("editor_%s" % field_edit_name, obj):
                    return default_block(request)

            if "fragment" in request.GET:
                buf2 = getattr(obj, field_edit_name)
                if buf2 == None:
                    buf2 = ""
                if request.GET["fragment"] == "header":
                    if "$$$" in buf2:
                        buf = buf + "$$$" + buf2.split("$$$")[1]
                elif request.GET["fragment"] == "footer":
                    buf = buf2.split("$$$")[0] + "$$$" + buf
                setattr(obj, field_edit_name, buf)
            else:
                setattr(obj, field_edit_name, buf)
            save(obj, request, "editor", {"field": field_edit_name})
            return HttpResponse("OK")
    else:
        obj = model.objects.get(id=pk)

        if (
            obj
            and hasattr(settings, "CANCAN")
            and is_in_cancan_rules(type(obj), request.ability.access_rules.rules)
        ):
            if not request.ability.can("editor_%s" % field_edit_name, obj):
                return default_block(request)

        table_name = model._meta.object_name
        txt = getattr(obj, field_edit_name)
        if txt == None:
            txt = ""

        if "fragment" in request.GET:
            if request.GET["fragment"] == "header":
                txt = txt.split("$$$")[0]
            elif request.GET["fragment"] == "footer":
                if "$$$" in txt:
                    txt = txt.split("$$$")[1]
                else:
                    txt = ""

        f = None
        for field in obj._meta.fields:
            if field.name == field_edit_name:
                f = field
                break

        x = request.get_full_path().split("?", 1)
        if len(x) > 1:
            get_param = "?" + x[1]
        else:
            get_param = ""

        if field_name:
            save_path = (
                app
                + "/table/"
                + tab
                + "/"
                + str(parent_pk)
                + "/"
                + table_name
                + "/"
                + str(pk)
                + "/"
                + field_edit_name
                + "/py/editor/"
                + get_param
            )
        else:
            save_path = (
                app
                + "/table/"
                + table_name
                + "/"
                + str(pk)
                + "/"
                + field_edit_name
                + "/py/editor/"
                + get_param
            )

        if not txt and hasattr(obj, "get_" + field_edit_name + "_if_empty"):
            txt = getattr(obj, "get_" + field_edit_name + "_if_empty")(
                request, template_name, ext, extra_context, target
            )

        c = {
            "app": app,
            "tab": table_name,
            "pk": pk,
            "object": obj,
            "field_name": field_edit_name,
            "ext": ext,
            "save_path": save_path,
            "txt": txt,
            "verbose_field_name": f.verbose_name,
        }
        t = None
        if hasattr(obj, "template_for_object"):
            t = obj.template_for_object(view_editor, c, ext)
        if not t:
            t = "schsys/db_field_edt.html"

        return render_to_response(
            # transform_template_name(obj, request, "schsys/db_field_edt.html"),
            t,
            context=c,
            request=request,
        )


class GenericTable(object):
    """GenericTable"""

    def __init__(self, urlpatterns, app, views_module=None):
        """Constructor

        Args:
            urlpatterns -
            app - application
            views_module - module

        """
        self.urlpatterns = urlpatterns
        self.app = app
        self.base_url = get_script_prefix()
        self.views_module = views_module

    def new_rows(
        self,
        tab,
        field=None,
        title="",
        title_plural="",
        template_name=None,
        extra_context=None,
        queryset=None,
        prefix=None,
    ):
        rows = GenericRows(self, prefix, title, title_plural)
        rows.tab = tab
        if field:
            rows.set_field(field)
        rows.extra_context = extra_context
        rows.base_path = "table/" + tab + "/"
        if template_name:
            rows.template_name = template_name
        else:
            if field:
                if "." in tab:
                    pos = tab.rfind(".")
                    m = apps.get_model(tab[:pos], tab[pos + 1 :])
                else:
                    m = apps.get_model(self.app, tab)
                try:
                    try:
                        f = getattr(m, field).rel
                    except:
                        f = getattr(m, field).related
                except:
                    for item in dir(m):
                        print(item)
                    print("----------")
                    print(field)
                    print("----------")

                try:
                    table_name = f.name
                except:
                    table_name = f.var_name
            else:
                table_name = tab.lower()
            if ":" in table_name:
                rows.template_name = (
                    self.app.lower() + "/" + table_name.split(":")[-1] + ".html"
                )
            else:
                rows.template_name = self.app.lower() + "/" + table_name + ".html"
        if "." in tab:
            rows.base_model = apps.get_model(tab)
        else:
            rows.base_model = apps.get_model(self.app + "." + tab)
        rows.queryset = queryset
        if "." in tab:
            pos = tab.rfind(".")
            rows.base_perm = tab[:pos] + ".%s_" + tab[pos + 1 :].lower()
        else:
            rows.base_perm = self.app + ".%s_" + tab.lower()
        return rows

    def append_from_schema(self, rows, schema):
        for char in schema.split(";"):
            if hasattr(rows, char):
                rows = getattr(rows, char)()

    def from_schema(
        self,
        schema,
        tab,
        field=None,
        title="",
        title_plural="",
        template_name=None,
        extra_context=None,
        queryset=None,
        prefix=None,
    ):
        if not title_plural:
            title_plural = title
        rows = self.new_rows(
            tab,
            field,
            title,
            title_plural,
            template_name,
            extra_context,
            queryset,
            prefix,
        )
        self.append_from_schema(rows, schema)
        return rows

    def standard(
        self,
        tab,
        title="",
        title_plural="",
        template_name=None,
        extra_context=None,
        queryset=None,
        prefix=None,
    ):
        schema = "add"
        rows = self.from_schema(
            schema,
            tab,
            None,
            title,
            title_plural,
            template_name,
            extra_context,
            queryset,
            prefix,
        )
        rows.set_field("this")
        rows.add().gen()

        schema = "list;detail;edit;add;delete;editor"
        return self.from_schema(
            schema,
            tab,
            None,
            title,
            title_plural,
            template_name,
            extra_context,
            queryset,
            prefix,
        ).gen()

    def for_field(
        self,
        tab,
        field,
        title="",
        title_plural="",
        template_name=None,
        extra_context=None,
        queryset=None,
        prefix=None,
    ):
        rows = self.new_rows(
            tab,
            field,
            title,
            title_plural,
            template_name,
            extra_context,
            queryset,
            prefix,
        )
        schema = "list;detail;edit;add;delete;editor"
        self.append_from_schema(rows, schema)
        return rows.gen()

    def tree(
        self,
        tab,
        title="",
        title_plural="",
        template_name=None,
        extra_context=None,
        queryset=None,
        prefix=None,
    ):
        return None


class GenericRows(object):
    def __init__(self, table, prefix, title="", title_plural="", parent_rows=None):
        self.table = table
        self.prefix = prefix
        self.field = None
        self.title = _(title)
        self.title_plural = _(title_plural)
        if parent_rows:
            self.base_path = parent_rows.base_path
            self.base_model = parent_rows.base_model
            self.base_perm = parent_rows.base_perm
            self.update_view = parent_rows.update_view
            self.field = parent_rows.field
            self.tab = parent_rows.tab
            self.title = parent_rows.title
            self.title_plural = parent_rows.title_plural
            self.template_name = parent_rows.template_name
            self.extra_context = parent_rows.extra_context
            self.queryset = parent_rows.queryset

    def _get_base_path(self):
        if self.field:
            if self.prefix:
                return (
                    self.base_path[:-1]
                    + "_"
                    + self.prefix
                    + "/"
                    + "(?P<parent_pk>-?\d+)/%s/" % self.field
                )
            else:
                return self.base_path + "(?P<parent_pk>-?\d+)/%s/" % self.field
        else:
            if self.prefix:
                return self.base_path[:-1] + "_" + self.prefix + "/"
            else:
                return self.base_path

    def table_paths_to_context(self, view_class, context):
        x = view_class.request.path.split("/table/", 1)
        x2 = x[1].split("/")

        bf = 0
        if (
            "base_filter" in view_class.kwargs
            and view_class.kwargs["base_filter"] != None
        ):
            bf = 1

        if "parent_pk" in view_class.kwargs:
            context["table_path"] = x[0] + "/table/" + "/".join(x2[:3]) + "/"
            context["table_path_and_base_filter"] = (
                x[0] + "/table/" + "/".join(x2[: 3 + bf]) + "/"
            )
            context["table_path_and_filter"] = (
                x[0] + "/table/" + "/".join(x2[:-3]) + "/"
            )
        else:
            context["table_path"] = x[0] + "/table/" + x2[0] + "/"
            if bf:
                context["table_path_and_base_filter"] = (
                    context["table_path"] + x2[1] + "/"
                )
            else:
                context["table_path_and_base_filter"] = context["table_path"]
            context["table_path_and_filter"] = (
                x[0] + "/table/" + "/".join(x2[:-3]) + "/"
            )

    def set_field(self, field=None):
        self.field = field
        return self

    def _append(self, url_str, fun, parm=None):
        if parm:
            self.table.urlpatterns += [
                re_path(self._get_base_path() + url_str, fun, parm),
            ]
        else:
            self.table.urlpatterns += [
                re_path(self._get_base_path() + url_str, fun),
            ]
        return self

    def gen(self):
        return self

    def list(self):
        url = r"((?P<base_filter>[\w=_,;-]*)/|)(?P<filter>[\w=_,;-]*)/(?P<target>[\w_-]*)/[_]?(?P<vtype>list|sublist|tree|get|gettree|treelist|table_action)/$"

        parent_class = self

        class ListView(generic.ListView):
            model = self.base_model
            queryset = self.queryset
            paginate_by = 64
            allow_empty = True
            template_name = self.template_name
            response_class = ExtTemplateResponse
            base_class = self
            form = None
            form_valid = None

            title = self.title_plural

            if self.extra_context:
                extra_context = self.extra_context
            else:
                extra_context = {}
            if self.field:
                rel_field = self.field
            else:
                rel_field = None

            sort = None
            order = None
            search = None

            def _context_for_tree(self):
                try:
                    parent_pk = int(self.kwargs["filter"])
                    if parent_pk > 0:
                        parent = self.model.objects.get(pk=parent_pk)
                    else:
                        parent = None
                except:
                    parent_pk = None
                    parent = None
                try:
                    base_parent_pk = int(self.kwargs["base_filter"])
                    if base_parent_pk > 0:
                        base_parent = self.model.objects.get(pk=base_parent_pk)
                    else:
                        base_parent = None
                except:
                    base_parent_pk = None
                    base_parent = None
                if not parent_pk and base_parent_pk:
                    parent_pk = base_parent_pk
                    parent = base_parent
                return {
                    "parent_pk": parent_pk,
                    "parent": parent,
                    "base_parent_pk": base_parent_pk,
                    "base_parent": base_parent,
                }

            def doc_type(self):
                for doc_type in DOC_TYPES:
                    if self.kwargs["target"].startswith(doc_type):
                        return doc_type
                if "json" in self.request.GET and self.request.GET["json"] == "1":
                    return "json"
                return "html"

            def get_template_names(self):
                names = super().get_template_names()
                if "target" in self.kwargs and "__" in self.kwargs["target"]:
                    target2 = self.kwargs["target"].split("__", 1)[1]
                    if "__" in target2:
                        app, t = target2.split("__")
                        names.insert(
                            0,
                            app
                            + "/"
                            + self.template_name.split("/")[-1].replace(
                                ".html", t + ".html"
                            ),
                        )
                    else:
                        names.insert(
                            0, self.template_name.replace(".html", target2 + ".html")
                        )
                if "version" in self.request.GET:
                    v = self.request.GET["version"]
                    if "__" in v:
                        x = v.split("__", 1)
                        y = self.template_name.split("/")
                        template2 = x[0] + "/" + y[-1].replace(".html", x[1] + ".html")
                    else:
                        template2 = self.template_name.replace(".html", v + ".html")
                    names.insert(0, template2)

                return names

            def get_paginate_by(self, queryset):
                if self.doc_type() in DOC_TYPES and self.doc_type() != "json":
                    return None
                else:
                    return self.paginate_by

            def get(self, request, *args, **kwargs):
                if "init" in kwargs:
                    kwargs["init"](self)

                if self.kwargs["vtype"] == "table_action":
                    parent = None
                    try:
                        try:
                            parent_id = int(self.kwargs["filter"])
                        except:
                            parent_id = 0
                        if parent_id > 0:
                            parent = self.model.objects.get(id=parent_id)
                        else:
                            if (
                                "base_filter" in self.kwargs
                                and self.kwargs["base_filter"]
                            ):
                                parent_id = int(self.kwargs["base_filter"])
                                parent = self.model.objects.get(id=parent_id)
                            elif (
                                "parent_pk" in self.kwargs and self.kwargs["parent_pk"]
                            ):
                                parent = self.model.objects.get(
                                    id=int(self.kwargs["parent_pk"])
                                )

                    except:
                        parent = None

                    model = self.get_queryset().model
                    if parent and hasattr(model, "get_derived_object"):
                        obj2 = model(parent=parent).get_derived_object(
                            {
                                "view": self,
                            }
                        )
                        model = type(obj2)

                    if hasattr(model, "table_action"):
                        data = request.POST
                        if request.content_type == "application/json":
                            try:
                                if type(request.body) == str:
                                    data = json_loads(request.body.strip())
                                else:
                                    data = json_loads(
                                        request.body.decode("utf-8").strip()
                                    )
                            except:
                                print("+++++++++++++++++++++++++++++++++++++++++")
                                print(request.body)
                                print("-----------------------------------------")
                                raise Http404("Invalid data format")

                        ret = getattr(model, "table_action")(self, request, data)
                        if ret == None:
                            raise Http404("Action doesn't exists")
                        else:
                            if type(ret) == str:
                                return HttpResponse(
                                    ret, content_type="application/json"
                                )
                            elif isinstance(ret, HttpResponse):
                                return ret
                            else:
                                return JsonResponse(ret, safe=False)
                    raise Http404("Action doesn't exists")

                if "tree" in self.kwargs["vtype"]:
                    c = self._context_for_tree()

                    # try:
                    #    parent = int(kwargs['filter'])
                    # except:
                    #    try:
                    #        parent = int(kwargs['base_filter'])
                    #    except:
                    #        parent = None

                    if c["parent_pk"] != None and c["parent_pk"] < 0:
                        parent_old = c["parent_pk"]
                        try:
                            parent = self.model.objects.get(
                                id=-1 * parent_old
                            ).parent.id
                        except:
                            parent = 0

                        path2 = ("/" + str(parent) + "/").join(
                            request.get_full_path().rsplit(
                                "/" + str(parent_old) + "/", 1
                            )
                        )
                        # path2 = request.get_full_path().replace(str(parent_old), str(parent))
                        return HttpResponseRedirect(path2)

                offset = request.GET.get("offset")

                self.sort = request.GET.get("sort")
                self.order = request.GET.get("order")
                self.search = request.GET.get("search")

                if offset:
                    self.kwargs["page"] = int(int(offset) / 64) + 1

                views_module = self.base_class.table.views_module

                form_name = None
                if "target" in self.kwargs and "__" in self.kwargs["target"]:
                    template_name = self.kwargs["target"].split("__")[-1]
                    form_name = (
                        "_FilterForm"
                        + self.model._meta.object_name
                        + "_"
                        + template_name
                    )
                    if not hasattr(views_module, form_name):
                        form_name = None
                if not form_name:
                    form_name = "_FilterForm" + self.model._meta.object_name
                    form_name_alt = None

                if hasattr(views_module, form_name):
                    if request.method == "POST":
                        self.form = getattr(views_module, form_name)(request.POST)
                        if self.form.is_valid():
                            self.form_valid = True
                        else:
                            self.form_valid = False
                    else:
                        self.form = getattr(views_module, form_name)()
                        self.form_valid = None

                return super(ListView, self).get(request, *args, **kwargs)

            def post(self, request, *args, **kwargs):
                return self.get(request, *args, **kwargs)

            def get_context_data(self, **kwargs):
                nonlocal parent_class
                context = super(ListView, self).get_context_data(**kwargs)
                context["view"] = self
                context["title"] = self.title
                context["rel_field"] = self.rel_field
                context["filter"] = self.kwargs["filter"]
                context["model"] = self.model
                if "__" in self.kwargs["target"]:
                    x = self.kwargs["target"].split("__", 1)
                    context["target"] = x[0]
                    context["version"] = x[1]
                else:
                    context["target"] = self.kwargs["target"]
                    context["version"] = ""
                if "version" in self.request.GET:
                    context["version"] = self.request.GET["version"]
                context["sort"] = self.sort
                context["order"] = self.order
                parent_class.table_paths_to_context(self, context)

                if "base_filter" in self.kwargs and self.kwargs["base_filter"]:
                    context["base_filter"] = self.kwargs["base_filter"]
                else:
                    context["base_filter"] = ""

                context["app_name"] = parent_class.table.app
                context["table_name"] = parent_class.tab

                if self.form:
                    context["form"] = self.form

                context["doc_type"] = self.doc_type()
                context["uuid"] = uuid.uuid4()
                context["vtype"] = self.kwargs["vtype"]
                context["parent_id"] = None

                if "tree" in self.kwargs["vtype"]:
                    c = self._context_for_tree()
                    context.update(c)

                context["kwargs"] = self.kwargs
                context["GET"] = self.request.GET
                context["POST"] = self.request.POST
                ret = transform_extra_context(context, self.extra_context)
                return ret

            def get_queryset(self):
                ret = None
                if "tree" in self.kwargs["vtype"]:
                    filter = self.kwargs["filter"]
                    parent = None
                    c = self._context_for_tree()
                    if hasattr(self.model, "filter") and not (
                        type(filter) == str and filter.isdigit()
                    ):
                        ret = self.model.filter(filter, self, self.request)
                    else:
                        if self.queryset:
                            ret = self.queryset
                        else:
                            if hasattr(settings, "CANCAN") and is_in_cancan_rules(
                                self.model, self.request.ability.access_rules.rules
                            ):
                                ret = self.request.ability.queryset_for(
                                    "view", self.model
                                )
                            else:
                                ret = self.model.objects.all()
                        if not "pk" in self.request.GET:
                            if c["parent_pk"]:
                                if c["parent_pk"] > 0:
                                    ret = ret.filter(parent=c["parent_pk"])
                                else:
                                    ret = ret.filter(parent=None)
                            else:
                                ret = ret.filter(parent=None)

                    if not "pk" in self.request.GET:
                        if (
                            (not filter or filter == "-")
                            and c["base_parent_pk"]
                            and c["base_parent_pk"] > 0
                        ):
                            ret = ret.filter(parent=c["base_parent_pk"])
                    # if not 'pk' in self.request.GET:
                    #    ret =  ret.filter(parent=parent)
                    ret = filter_by_permissions(self, self.model, ret, self.request)
                else:
                    if self.queryset:
                        ret = self.queryset
                    else:
                        if self.rel_field:
                            ppk = int(self.kwargs["parent_pk"])
                            parent = self.model.objects.get(id=ppk)
                            self.extra_context["parent"] = parent
                            f = getattr(parent, self.rel_field)
                            ret = f.all()
                        else:
                            filter = self.kwargs["filter"]
                            if filter and filter != "-":
                                if hasattr(self.model, "filter"):
                                    ret = self.model.filter(filter, self, self.request)
                                else:
                                    if hasattr(
                                        settings, "CANCAN"
                                    ) and is_in_cancan_rules(
                                        self.model,
                                        self.request.ability.access_rules.rules,
                                    ):
                                        ret = self.request.ability.queryset_for(
                                            "view", self.model
                                        )
                                    else:
                                        ret = self.model.objects.all()
                            else:
                                if hasattr(settings, "CANCAN") and is_in_cancan_rules(
                                    self.model, self.request.ability.access_rules.rules
                                ):
                                    ret = self.request.ability.queryset_for(
                                        "view", self.model
                                    )
                                else:
                                    ret = self.model.objects.all()
                    ret = filter_by_permissions(self, self.model, ret, self.request)
                    if "base_filter" in self.kwargs and self.kwargs["base_filter"]:
                        try:
                            parent = int(self.kwargs["base_filter"])
                            ret = ret.filter(parent=parent)
                        except:
                            pass
                if self.search:
                    fields = [
                        f
                        for f in self.model._meta.fields
                        if isinstance(f, django.db.models.CharField)
                    ]
                    queries = [
                        Q(**{f.name + "__icontains": self.search}) for f in fields
                    ]
                    qs = Q()
                    for query in queries:
                        qs = qs | query
                    ret = ret.filter(qs)

                if hasattr(self.model, "sort"):
                    ret = self.model.sort(ret, self.sort, self.order)
                else:
                    if self.sort == "cid":
                        if self.order == "asc":
                            ret = ret.order_by("id")
                        else:
                            ret = ret.order_by("-id")

                if "pk" in self.request.GET:
                    ret = ret.filter(pk=self.request.GET["pk"])
                    return ret
                else:
                    if self.form and not self.rel_field:
                        if self.form_valid == True:
                            return self.form.process(self.request, ret)
                        else:
                            if hasattr(self.form, "process_empty_or_invalid"):
                                return self.form.process_empty_or_invalid(
                                    self.request, ret
                                )
                            else:
                                return ret
                    else:
                        return ret

        VIEWS_REGISTER["list"][self.base_model] = ListView

        fun = make_perms_test_fun(
            parent_class.table.app,
            self.base_model,
            self.base_perm % "list",
            ListView.as_view(),
        )
        self._append(url, fun)

        return self

    def detail(self):
        url = r"(?P<pk>\d+)/(?P<target>[\w_]*)/(?P<vtype>view|row_action)/$"
        parent_class = self

        class DetailView(generic.DetailView):
            queryset = self.queryset

            if self.field:
                try:
                    f = getattr(self.base_model, self.field).related
                except:
                    f = getattr(self.base_model, self.field).rel
                model = f.related_model
            else:
                model = self.base_model

            template_name = self.template_name
            title = self.title
            response_class = ExtTemplateResponse

            def get_object(self, queryset=None):
                obj = super().get_object(queryset)
                if hasattr(obj, "get_derived_object"):
                    obj2 = obj.get_derived_object(
                        {
                            "view": self,
                        }
                    )
                    self.model = type(obj2)
                    return obj2
                else:
                    return obj

            def doc_type(self):
                for doc_type in DOC_TYPES:
                    if self.kwargs["target"].startswith(doc_type):
                        return doc_type
                if "json" in self.request.GET and self.request.GET["json"] == "1":
                    return "json"
                return "html"

            def get_template_names(self):
                names = super().get_template_names()
                if "target" in self.kwargs and self.kwargs["target"].startswith("ver"):
                    names.insert(
                        0,
                        self.template_name.replace(
                            ".html", self.kwargs["target"][3:] + ".html"
                        ),
                    )
                if "version" in self.request.GET:
                    v = self.request.GET["version"]
                    if "__" in v:
                        x = v.split("__", 1)
                        y = self.template_name.split("/")
                        template2 = x[0] + "/" + y[-1].replace(".html", x[1] + ".html")
                    else:
                        template2 = self.template_name.replace(".html", v + ".html")
                    names.insert(0, template2)
                return names

            def get_context_data(self, **kwargs):
                nonlocal parent_class
                context = super(DetailView, self).get_context_data(**kwargs)
                context["view"] = self
                context["title"] = self.title + " - " + str(_("element information"))
                if "version" in self.request.GET:
                    context["version"] = self.request.GET["version"]

                parent_class.table_paths_to_context(self, context)

                return context

            def get(self, request, *args, **kwargs):
                self.object = self.get_object()

                if (
                    self.object
                    and hasattr(settings, "CANCAN")
                    and is_in_cancan_rules(
                        type(self.object), self.request.ability.access_rules.rules
                    )
                ):
                    if not self.request.ability.can("detail", self.object):
                        return default_block(request)

                if self.kwargs["vtype"] == "row_action":
                    if hasattr(self.object, "row_action"):
                        ret = getattr(self.model, "row_action")(
                            self.model, request, args, kwargs
                        )
                        if ret == None:
                            raise Http404("Action doesn't exists")
                        else:
                            return JsonResponse(ret)
                    raise Http404("Action doesn't exists")

                return super(generic.DetailView, self).get(request, *args, **kwargs)

            def post(self, request, *args, **kwargs):
                return self.get(request, *args, **kwargs)

        VIEWS_REGISTER["detail"][self.base_model] = DetailView

        fun = make_perms_test_fun(
            parent_class.table.app,
            self.base_model,
            self.base_perm % "view",
            DetailView.as_view(),
        )
        return self._append(url, fun)

    def edit(self):
        url = r"(?P<pk>\d+)/edit/$"
        parent_class = self

        class UpdateView(generic.UpdateView):
            doc_type = "html"
            response_class = ExtTemplateResponse

            if self.field:
                try:
                    f = getattr(self.base_model, self.field).related
                except:
                    f = getattr(self.base_model, self.field).rel
                model = f.related_model
            else:
                model = self.base_model
            success_url = make_path_lazy("ok")

            template_name = self.template_name
            title = self.title
            fields = "__all__"

            def get_object(self, queryset=None):
                obj = super().get_object(queryset)
                if hasattr(obj, "get_derived_object"):
                    obj2 = obj.get_derived_object(
                        {
                            "view": self,
                        }
                    )
                    self.model = type(obj2)
                    return obj2
                else:
                    return obj

            def doc_type(self):
                return "html"

            def get_template_names(self):
                names = super().get_template_names()
                if "target" in self.kwargs and self.kwargs["target"].startswith("ver"):
                    names.insert(
                        0,
                        self.template_name.replace(
                            ".html", self.kwargs["target"][3:] + ".html"
                        ),
                    )
                if "version" in self.request.GET:
                    v = self.request.GET["version"]
                    if "__" in v:
                        x = v.split("__", 1)
                        y = self.template_name.split("/")
                        template2 = x[0] + "/" + y[-1].replace(".html", x[1] + ".html")
                    else:
                        template2 = self.template_name.replace(".html", v + ".html")
                    names.insert(0, template2)
                return names

            def get_context_data(self, **kwargs):
                nonlocal parent_class
                context = super(UpdateView, self).get_context_data(**kwargs)
                context["view"] = self
                context["title"] = self.title + " - " + str(_("update element"))
                if "version" in self.request.GET:
                    context["version"] = self.request.GET["version"]

                # context['prj'] = ""

                parent_class.table_paths_to_context(self, context)

                # for app in settings.APPS:
                #    if '.' in app and parent_class.table.app in app:
                #        _app = app.split('.')[0]
                #        if not _app.startswith('_'):
                #            context['prj'] = app.split('.')[0]
                #        break
                return context

            def get(self, request, *args, **kwargs):
                self.object = self.get_object()

                if (
                    self.object
                    and hasattr(settings, "CANCAN")
                    and is_in_cancan_rules(
                        type(self.object), self.request.ability.access_rules.rules
                    )
                ):
                    if not self.request.ability.can("change", self.object):
                        return default_block(request)

                if self.object and hasattr(self.object, "redirect_href"):
                    href = self.object.redirect_href(self, request)
                    if href:
                        return HttpResponseRedirect(href)

                if "init" in kwargs:
                    kwargs["init"](self)

                if self.object and hasattr(self.object, "get_form_class"):
                    self.form_class = self.object.get_form_class(self, request, False)
                else:
                    self.form_class = self.get_form_class()

                form = None
                if self.object and hasattr(self.object, "get_form"):
                    form = self.object.get_form(self, request, self.form_class, False)
                if not form:
                    form = self.get_form(self.form_class)
                if form:
                    for field in form.fields:
                        if hasattr(form.fields[field].widget, "py_client"):
                            if request.META["HTTP_USER_AGENT"].startswith("Py"):
                                form.fields[field].widget.set_py_client(True)
                return self.render_to_response(self.get_context_data(form=form))

            def post(self, request, *args, **kwargs):
                self.object = self.get_object()

                if (
                    self.object
                    and hasattr(settings, "CANCAN")
                    and is_in_cancan_rules(
                        type(self.object), self.request.ability.access_rules.rules
                    )
                ):
                    if not self.request.ability.can("change", self.object):
                        return default_block(request)

                if "init" in kwargs:
                    kwargs["init"](self)

                if self.object and hasattr(self.object, "get_form_class"):
                    self.form_class = self.object.get_form_class(self, request, False)
                else:
                    self.form_class = self.get_form_class()

                form = None
                if self.object and hasattr(self.object, "get_form"):
                    form = self.object.get_form(self, request, self.form_class, False)
                if not form:
                    form = self.get_form(self.form_class)
                if self.model and hasattr(self.model, "is_form_valid"):

                    def vfun():
                        return self.model.is_form_valid(form)

                else:
                    vfun = form.is_valid

                if vfun():
                    return self.form_valid(form, request)
                else:
                    print("INVALID:", form.errors)
                    return self.form_invalid(form)

            def form_valid(self, form, request=None):
                """
                If the form is valid, save the associated model.
                """
                jsondata = {}
                for key, value in form.data.items():
                    if key.startswith("json_"):
                        jsondata[key[5:]] = value

                self.object = form.save(commit=False)
                if jsondata:
                    self.object.jsondata = jsondata

                if hasattr(self.object, "post_form"):
                    if self.object.post_form(self, form, request):
                        save(self.object, request, "edit")
                else:
                    save(self.object, request, "edit")
                form.save_m2m()

                if self.object:
                    return update_row_ok(request, int(self.object.id), self.object)
                else:
                    return super(generic.edit.ModelFormMixin, self).form_valid(form)

        VIEWS_REGISTER["edit"][self.base_model] = UpdateView

        fun = make_perms_test_fun(
            parent_class.table.app,
            self.base_model,
            self.base_perm % "change",
            UpdateView.as_view(),
        )
        return self._append(url, fun)

    def add(self):
        url = r"(?P<add_param>[\w=_-]*)/add/$"
        parent_class = self

        class CreateView(generic.CreateView):
            response_class = ExtTemplateResponse
            if self.field and self.field != "this":
                try:
                    f = getattr(self.base_model, self.field).related
                except:
                    f = getattr(self.base_model, self.field).rel
                model = f.related_model
                pmodel = self.base_model
            else:
                model = self.base_model
                pmodel = model
            template_name = self.template_name
            title = self.title
            field = self.field
            init_form = None
            fields = "__all__"

            def get_object(self, queryset=None):
                obj = self.model()
                if hasattr(obj, "get_derived_object"):
                    obj2 = obj.get_derived_object(
                        {
                            "view": self,
                        }
                    )
                    self.model = type(obj2)
                    return obj2
                else:
                    return obj

            def doc_type(self):
                return "html"

            def get_template_names(self):
                names = super().get_template_names()
                if "target" in self.kwargs and self.kwargs["target"].startswith("ver"):
                    names.insert(
                        0,
                        self.template_name.replace(
                            ".html", self.kwargs["target"][3:] + ".html"
                        ),
                    )
                if "version" in self.request.GET:
                    v = self.request.GET["version"]
                    if "__" in v:
                        x = v.split("__", 1)
                        y = self.template_name.split("/")
                        template2 = x[0] + "/" + y[-1].replace(".html", x[1] + ".html")
                    else:
                        template2 = self.template_name.replace(".html", v + ".html")
                    names.insert(0, template2)

                return names

            def get_success_url(self):
                # if self.object:
                #    success_url = make_path_lazy(
                #        "new_row_ok", (int(self.object.id), str(self.object))
                #    )
                # else:
                #    success_url = make_path_lazy("ok")
                # return success_url
                return make_path_lazy("ok")

            def _get_form(self, request, *args, **kwargs):
                # self.object = self.model()
                self.object = self.get_object()
                if self.field:
                    ppk = int(kwargs["parent_pk"])
                    if ppk > 0:
                        m = self.pmodel
                        while m:
                            try:
                                self.object.parent = m.objects.get(id=ppk)
                                m = None
                            except:
                                m = m.__bases__[0]
                        # try:
                        #    self.object.parent = self.pmodel.objects.get(id=ppk)
                        # except:
                        #    try:
                        #        self.object.parent = self.pmodel.__bases__[
                        #            0
                        #        ].objects.get(id=ppk)
                        #    except:
                        #        self.object.parent = (
                        #            self.pmodel.__bases__[0]
                        #            .__bases__[0]
                        #            .objects.get(id=ppk)
                        #        )

                if hasattr(self.model, "init_new"):
                    if kwargs["add_param"] and kwargs["add_param"] != "-":
                        self.init_form = self.object.init_new(
                            request, self, kwargs["add_param"]
                        )
                    else:
                        self.init_form = self.object.init_new(request, self)
                    if self.init_form:
                        for pos in self.init_form:
                            if hasattr(self.object, pos):
                                try:
                                    setattr(self.object, pos, self.init_form[pos])
                                except:
                                    pass
                else:
                    self.init_form = None

                if self.object and hasattr(self.object, "get_form_class"):
                    self.form_class = self.object.get_form_class(self, request, True)
                else:
                    self.form_class = self.get_form_class()
                form = None
                if self.object and hasattr(self.object, "get_form"):
                    form = self.object.get_form(self, request, self.form_class, False)
                if not form:
                    form = self.get_form(self.form_class)

                return form

            def get(self, request, *args, **kwargs):
                form = self._get_form(request, *args, **kwargs)

                if (
                    self.object
                    and hasattr(settings, "CANCAN")
                    and is_in_cancan_rules(
                        type(self.object), self.request.ability.access_rules.rules
                    )
                ):
                    if not self.request.ability.can("add", self.object):
                        return default_block(request)

                if form:
                    for field in form.fields:
                        if hasattr(form.fields[field].widget, "py_client"):
                            if request.META["HTTP_USER_AGENT"].startswith("Py"):
                                form.fields[field].widget.set_py_client(True)

                if self.object and hasattr(self.object, "redirect_href"):
                    href = self.object.redirect_href(self, request)
                    if href:
                        return HttpResponseRedirect(href)
                return self.render_to_response(context=self.get_context_data(form=form))

            def post(self, request, *args, **kwargs):
                form = self._get_form(request, *args, **kwargs)

                if (
                    self.object
                    and hasattr(settings, "CANCAN")
                    and is_in_cancan_rules(
                        type(self.object), self.request.ability.access_rules.rules
                    )
                ):
                    if not self.request.ability.can("add", self.object):
                        return default_block(request)

                if self.model and hasattr(self.model, "is_form_valid"):

                    def vfun():
                        return self.model.is_form_valid(form)

                else:
                    vfun = form.is_valid
                if vfun():
                    return self.form_valid(form, request)
                else:
                    print("INVALID:", form.errors)
                    return self.form_invalid(form)

            def get_initial(self):
                d = super(CreateView, self).get_initial()

                for field in self.model._meta.fields:
                    if field.name in self.request.GET:
                        value = convert_str_to_model_field(
                            self.request.GET[field.name], field
                        )
                        d[field.name] = value

                if self.field:
                    if int(self.kwargs["parent_pk"]) > 0:
                        d["parent"] = self.kwargs["parent_pk"]
                    else:
                        d["parent"] = None
                if self.init_form:
                    transform_extra_context(d, self.init_form)
                return d

            def get_form_kwargs(self):
                ret = super(CreateView, self).get_form_kwargs()
                if self.init_form:
                    if "data" in ret:
                        data = ret["data"].copy()
                        for key, value in self.init_form.items():
                            if key in data and data[key]:
                                continue
                            data[key] = value

                        ret.update({"data": data})

                return ret

            def form_valid(self, form, request=None):
                """
                If the form is valid, save the associated model.
                """
                nonlocal parent_class
                jsondata = {}
                for key, value in form.data.items():
                    if key.startswith("json_"):
                        jsondata[key[5:]] = value

                self.object = form.save(commit=False)

                if jsondata:
                    self.object.jsondata = jsondata

                if "parent_pk" in self.kwargs and hasattr(self.object, "parent_id"):
                    if int(self.kwargs["parent_pk"]) != 0:
                        self.object.parent_id = int(self.kwargs["parent_pk"])

                if request and request.POST:
                    p = request.POST
                else:
                    p = {}
                if self.init_form:
                    for pos in self.init_form:
                        if hasattr(self.object, pos) and not pos in p:
                            try:
                                setattr(self.object, pos, self.init_form[pos])
                            except:
                                pass

                if hasattr(self.object, "post_form"):
                    if self.object.post_form(self, form, request):
                        save(self.object, request, "add")
                else:
                    save(self.object, request, "add")
                form.save_m2m()

                if self.object:
                    if "redirect" in self.request.GET and self.request.GET["redirect"]:
                        ctx = self.get_context_data(form=form)
                        tp = ctx["table_path"]
                        return HttpResponseRedirect(tp + ("%d/edit/" % self.object.pk))
                    else:
                        return new_row_ok(request, int(self.object.id), self.object)
                else:
                    return super(generic.edit.ModelFormMixin, self).form_valid(form)

            def get_context_data(self, **kwargs):
                nonlocal parent_class
                context = super(CreateView, self).get_context_data(**kwargs)
                context["view"] = self
                context["title"] = self.title + " - " + str(_("new element"))
                context["object"] = self.object
                context["add_param"] = self.kwargs["add_param"]
                if "version" in self.request.GET:
                    context["version"] = self.request.GET["version"]

                # context['prj'] = ""

                parent_class.table_paths_to_context(self, context)

                # for app in settings.APPS:
                #    if '.' in app and parent_class.table.app in app:
                #        _app = app.split('.')[0]
                #        if not _app.startswith('_'):
                #            context['prj'] = app.split('.')[0]
                #        break

                return context

        VIEWS_REGISTER["create"][self.base_model] = CreateView

        fun = make_perms_test_fun(
            parent_class.table.app,
            self.base_model,
            self.base_perm % "add",
            CreateView.as_view(),
        )
        return self._append(url, fun)

    def delete(self):
        url = r"(?P<pk>\d+)/delete/$"
        parent_class = self

        class DeleteView(generic.DeleteView):
            response_class = LocalizationTemplateResponse
            if self.field:
                try:
                    f = getattr(self.base_model, self.field).related
                except:
                    f = getattr(self.base_model, self.field).rel
                model = f.related_model
            else:
                model = self.base_model
            success_url = make_path_lazy("ok")
            template_name = self.template_name
            title = self.title

            def get_object(self, queryset=None):
                obj = super().get_object(queryset)
                if hasattr(obj, "get_derived_object"):
                    obj2 = obj.get_derived_object(
                        {
                            "view": self,
                        }
                    )
                    self.model = type(obj2)
                    return obj2
                else:
                    return obj

            def get_context_data(self, **kwargs):
                nonlocal parent_class
                context = super(DeleteView, self).get_context_data(**kwargs)
                context["view"] = self
                context["title"] = self.title + " - " + str(_("delete element"))
                if "version" in self.request.GET:
                    context["version"] = self.request.GET["version"]

                parent_class.table_paths_to_context(self, context)

                # context['prj'] = ""
                # for app in settings.APPS:
                #    if '.' in app and parent_class.table.app in app:
                #        _app = app.split('.')[0]
                #        if not _app.startswith('_'):
                #            context['prj'] = app.split('.')[0]
                #        break
                return context

            def get_template_names(self):
                names = super().get_template_names()
                if "target" in self.kwargs and self.kwargs["target"].startswith("ver"):
                    names.insert(
                        0,
                        self.template_name.replace(
                            ".html", self.kwargs["target"][3:] + ".html"
                        ),
                    )
                if "version" in self.request.GET:
                    v = self.request.GET["version"]
                    if "__" in v:
                        x = v.split("__", 1)
                        y = self.template_name.split("/")
                        template2 = x[0] + "/" + y[-1].replace(".html", x[1] + ".html")
                    else:
                        template2 = self.template_name.replace(".html", v + ".html")
                    names.insert(0, template2)
                return names

            def get(self, request, *args, **kwargs):
                self.object = self.get_object(self.queryset)
                if (
                    self.object
                    and hasattr(settings, "CANCAN")
                    and is_in_cancan_rules(
                        type(self.object), self.request.ability.access_rules.rules
                    )
                ):
                    if not self.request.ability.can("delete", self.object):
                        return default_block(request)

                return super().get(request, *args, **kwargs)

            def post(self, request, *args, **kwargs):
                self.object = self.get_object(self.queryset)
                if (
                    self.object
                    and hasattr(settings, "CANCAN")
                    and is_in_cancan_rules(
                        type(self.object), self.request.ability.access_rules.rules
                    )
                ):
                    if not self.request.ability.can("delete", self.object):
                        return default_block(request)

                if hasattr(self.object, "on_delete"):
                    self.object.on_delete(request, self)

                pk = int(self.object.id)

                super().post(request, *args, **kwargs)

                return delete_row_ok(request, pk, self.object)
                # return super().post(request, *args, **kwargs)

        VIEWS_REGISTER["delete"][self.base_model] = DeleteView

        fun = make_perms_test_fun(
            parent_class.table.app,
            self.base_model,
            self.base_perm % "delete",
            DeleteView.as_view(),
        )
        return self._append(url, fun)

    def editor(self):
        url = r"(?P<pk>\d+)/(?P<field_edit_name>[\w_]*)/(?P<target>[\w_]*)/editor/$"
        fun = make_perms_test_fun(
            self.table.app, self.base_model, self.base_perm % "change", view_editor
        )
        if self.field:
            try:
                f = getattr(self.base_model, self.field).related
            except:
                f = getattr(self.base_model, self.field).rel
            model = f.related_model
        else:
            model = self.base_model

        parm = dict(
            app=self.table.app,
            tab=self.tab,
            ext="py",
            model=model,
            post_save_redirect=make_path_lazy("ok"),
            template_name=self.template_name,
            extra_context=transform_extra_context(
                {"title": self.title + " - " + str(_("update element"))},
                self.extra_context,
            ),
        )
        return self._append(url, fun, parm)


def generic_table(
    urlpatterns,
    app,
    tab,
    title="",
    title_plural="",
    template_name=None,
    extra_context=None,
    queryset=None,
    views_module=None,
):
    GenericTable(urlpatterns, app, views_module).new_rows(
        tab, None, title, title_plural, template_name, extra_context, queryset
    ).list().detail().edit().add().delete().editor().gen()


def generic_table_start(urlpatterns, app, views_module=None):
    """Start generic table urls

    Args:
        urlpatterns - urlpatterns object defined in urls.py
        app - name of app
        views_module - imported views.py module
    """
    return GenericTable(urlpatterns, app, views_module)


def extend_generic_view(view_name, model, method_name, new_method):
    try:
        cls = VIEWS_REGISTER[view_name][model]
    except:
        cls = None
    if cls:
        old_method = getattr(cls, method_name)
        setattr(cls, method_name, new_method)
        if old_method:
            arch_method_name = "old_" + method_name
            if getattr(cls, arch_method_name):
                getattr(cls, arch_method_name).append(old_method)
            else:
                setattr(
                    cls,
                    arch_method_name,
                    [
                        new_method,
                    ],
                )
