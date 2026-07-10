"""ListView for schviews generic views."""

import uuid

import django
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.views import generic

from pytigon_lib.schtools.schjson import json_loads
from pytigon_lib.schviews.schrules import (
    filter_queryset_by_rules,
    is_rules_active,
)
from pytigon_lib.schviews.viewtools import DOC_TYPES, ExtTemplateResponse

from .._utils import transform_extra_context
from ..mixins import TemplateVariantListViewMixin
from ..perms import filter_by_permissions


def _create_list_view(parent_rows):
    url = r"((?P<base_filter>[\w=_,;-]*)/|)(?P<filter>[\w=_,;-]*)/(?P<target>[\w_-]*)/[_]?(?P<vtype>list|sublist|tree|get|gettree|treelist|table_action)/$"  # noqa: E501

    class ListView(TemplateVariantListViewMixin, generic.ListView):
        model = parent_rows.base_model
        queryset = parent_rows.queryset
        paginate_by = 64
        allow_empty = True
        template_name = parent_rows.template_name
        response_class = ExtTemplateResponse
        base_class = parent_rows

        form = None
        form_valid = None

        title = parent_rows.title_plural

        if parent_rows.extra_context:
            extra_context = parent_rows.extra_context
        else:
            extra_context = {}
        if parent_rows.field:
            rel_field = parent_rows.field
        else:
            rel_field = None

        sort = None
        order = None
        search = None

        def _context_for_tree(self):
            try:
                parent_pk = int(self.kwargs["filter"])
                parent = (
                    self.model.objects.get(pk=parent_pk) if parent_pk > 0 else None
                )
            except (ValueError, self.model.DoesNotExist):
                parent_pk = None
                parent = None
            try:
                base_parent_pk = int(self.kwargs["base_filter"])
                base_parent = (
                    self.model.objects.get(pk=base_parent_pk)
                    if base_parent_pk > 0
                    else None
                )
            except (ValueError, KeyError, self.model.DoesNotExist):
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

        def get_paginate_by(self, queryset):
            if self.doc_type() in DOC_TYPES and self.doc_type() != "json":
                return None
            return self.paginate_by

        def get(self, request, *args, **kwargs):
            if "init" in kwargs:
                kwargs["init"](self)

            if self.kwargs["vtype"] == "table_action":
                parent = None
                try:
                    try:
                        parent_id = int(self.kwargs["filter"])
                    except ValueError:
                        parent_id = 0
                    if parent_id > 0:
                        parent = self.model.objects.get(id=parent_id)
                    else:
                        if self.kwargs.get("base_filter"):
                            parent_id = int(self.kwargs["base_filter"])
                            parent = self.model.objects.get(id=parent_id)
                        elif self.kwargs.get("parent_pk"):
                            parent = self.model.objects.get(
                                id=int(self.kwargs["parent_pk"])
                            )
                except self.model.DoesNotExist:
                    parent = None

                model = self.get_queryset().model
                if parent and hasattr(model, "get_derived_object"):
                    obj2 = model(parent=parent).get_derived_object({"view": self})
                    model = type(obj2)

                if hasattr(model, "table_action"):
                    data = request.POST
                    if request.content_type == "application/json":
                        try:
                            if isinstance(request.body, str):
                                data = json_loads(request.body.strip())
                            else:
                                data = json_loads(
                                    request.body.decode("utf-8").strip()
                                )
                        except ValueError:
                            raise Http404("Invalid data format")

                    ret = getattr(model, "table_action")(self, request, data)
                    if ret is None:
                        raise Http404("Action doesn't exists")
                    if isinstance(ret, str):
                        return HttpResponse(ret, content_type="application/json")
                    if isinstance(ret, HttpResponse):
                        return ret
                    return JsonResponse(ret, safe=False)
                raise Http404("Action doesn't exists")

            if "tree" in self.kwargs["vtype"]:
                c = self._context_for_tree()
                if c["parent_pk"] is not None and c["parent_pk"] < 0:
                    parent_old = c["parent_pk"]
                    try:
                        parent = self.model.objects.get(
                            id=-1 * parent_old
                        ).parent.id
                    except (self.model.DoesNotExist, AttributeError):
                        parent = 0

                    path2 = ("/" + str(parent) + "/").join(
                        request.get_full_path().rsplit(
                            "/" + str(parent_old) + "/", 1
                        )
                    )
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
                    f"_FilterForm{self.model._meta.object_name}_{template_name}"
                )
                if not hasattr(views_module, form_name):
                    form_name = None
            if not form_name:
                form_name = f"_FilterForm{self.model._meta.object_name}"

            if hasattr(views_module, form_name):
                if request.method == "POST":
                    self.form = getattr(views_module, form_name)(request.POST)
                    self.form_valid = self.form.is_valid()
                else:
                    self.form = getattr(views_module, form_name)()
                    self.form_valid = None

            return super().get(request, *args, **kwargs)

        def post(self, request, *args, **kwargs):
            return self.get(request, *args, **kwargs)

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
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
            self.base_class.table_paths_to_context(self, context)

            if self.kwargs.get("base_filter"):
                context["base_filter"] = self.kwargs["base_filter"]
            else:
                context["base_filter"] = ""

            context["app_name"] = self.base_class.table.app
            context["table_name"] = self.base_class.tab

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
                c = self._context_for_tree()
                if hasattr(self.model, "filter") and not (
                    isinstance(filter, str) and filter.isdigit()
                ):
                    ret = self.model.filter(filter, self, self.request)
                else:
                    if self.queryset:
                        ret = self.queryset
                    else:
                        if is_rules_active():
                            ret = filter_queryset_by_rules(
                                self.request.user, "view", self.model
                            )
                        else:
                            ret = self.model.objects.all()
                    if "pk" not in self.request.GET:
                        if c["parent_pk"]:
                            if c["parent_pk"] > 0:
                                ret = ret.filter(parent=c["parent_pk"])
                            else:
                                ret = ret.filter(parent=None)
                        else:
                            ret = ret.filter(parent=None)

                if "pk" not in self.request.GET:
                    if (
                        (not filter or filter == "-")
                        and c["base_parent_pk"]
                        and c["base_parent_pk"] > 0
                    ):
                        ret = ret.filter(parent=c["base_parent_pk"])
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
                                if is_rules_active():
                                    ret = filter_queryset_by_rules(
                                        self.request.user, "view", self.model
                                    )
                                else:
                                    ret = self.model.objects.all()
                        else:
                            if is_rules_active():
                                ret = filter_queryset_by_rules(
                                    self.request.user, "view", self.model
                                )
                            else:
                                ret = self.model.objects.all()
                ret = filter_by_permissions(self, self.model, ret, self.request)
                if self.kwargs.get("base_filter"):
                    try:
                        parent = int(self.kwargs["base_filter"])
                        ret = ret.filter(parent=parent)
                    except ValueError:
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
            if self.form and not self.rel_field:
                if self.form_valid:
                    return self.form.process(self.request, ret)
                if hasattr(self.form, "process_empty_or_invalid"):
                    return self.form.process_empty_or_invalid(self.request, ret)
                return ret
            return ret

    return url, ListView
