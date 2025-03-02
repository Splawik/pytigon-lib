"""
This module provides generic templates and utility functions for handling views and URL patterns in a Django application.

Classes:
    GenericTable: Handles URL patterns and views for a table.
    GenericRows: Handles rows in a table.

Functions:
    make_path(view_name: str, args: Optional[List[Any]] = None) -> str:
        Generate a URL path for a given view name and optional arguments.

    make_path_lazy: Lazy version of make_path.

    convert_str_to_model_field(s: str, field: Any) -> Any:
        Convert a string to the appropriate type based on the model field type.

    gen_tab_action(table: str, action: str, fun: Callable, extra_context: Optional[Dict] = None) -> path:
        Generate a URL pattern for a table action.

    gen_tab_field_action(table: str, field: str, action: str, fun: Callable, extra_context: Optional[Dict] = None) -> path:
        Generate a URL pattern for a table field action.

    gen_row_action(table: str, action: str, fun: Callable, extra_context: Optional[Dict] = None) -> path:
        Generate a URL pattern for a row action.

    transform_extra_context(context1: Dict, context2: Optional[Dict]) -> Dict:
        Merge two context dictionaries, evaluating callables in context2.

    save(obj: Any, request: Any, view_type: str, param: Optional[Dict] = None) -> None:
        Save an object, optionally using a custom save method.

    view_editor(request: Any, pk: int, app: str, tab: str, model: Any, template_name: str, field_edit_name: str, post_save_redirect: str, ext: str = "py", extra_context: Optional[Dict] = None, target: Optional[str] = None, parent_pk: int = 0, field_name: Optional[str] = None) -> HttpResponse:
        Handle editor view for a model field.

    generic_table(urlpatterns, app, tab, title="", title_plural="", template_name=None, extra_context=None, queryset=None, views_module=None):
        Create a generic table with standard views.

    generic_table_start(urlpatterns, app, views_module=None):
        Start generic table URLs.

    extend_generic_view(view_name, model, method_name, new_method):
        Extend a generic view with a new method.
"""

import uuid
import datetime
import django
from typing import Any, Callable, Dict, List, Optional, Type

from django.urls import get_script_prefix, reverse
from django.apps import apps
from django.views import generic
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect, Http404
from django.utils.functional import lazy
from django.conf import settings
from django.urls import path, re_path
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from pytigon_lib.schviews.actions import new_row_ok, update_row_ok, delete_row_ok
from pytigon_lib.schviews.viewtools import render_to_response
from pytigon_lib.schtools.schjson import json_loads
from pytigon_lib.schtools.tools import is_in_cancan_rules

from .viewtools import (
    LocalizationTemplateResponse,
    ExtTemplateResponse,
    DOC_TYPES,
)

from .perms import make_perms_test_fun, filter_by_permissions, default_block

VIEWS_REGISTER = {"list": {}, "detail": {}, "edit": {}, "create": {}, "delete": {}}


def make_path(view_name: str, args: Optional[List[Any]] = None) -> str:
    """
    Generate a URL path for a given view name and optional arguments.

    Args:
        view_name (str): The name of the view for which to generate the URL path.
        args (Optional[List[Any]]): A list of optional arguments to include in the URL path.

    Returns:
        str: The generated URL path.
    """
    if settings.URL_ROOT_FOLDER:
        return f"{settings.URL_ROOT_FOLDER}/{reverse(view_name, args=args)}"
    return reverse(view_name, args=args)


make_path_lazy = lazy(make_path, str)


def _isinstance(field: Any, instances: List[Type]) -> bool:
    """Check if a field is an instance of any type in the given list."""
    return any(isinstance(field, instance) for instance in instances)


def convert_str_to_model_field(s: str, field: Any) -> Any:
    """Convert a string to the appropriate type based on the model field type."""
    if _isinstance(field, (django.db.models.CharField, django.db.models.TextField)):
        return s
    elif _isinstance(field, (django.db.models.DateTimeField,)):
        return datetime.datetime.fromisoformat(s[:19])
    elif _isinstance(field, (django.db.models.DateField,)):
        return datetime.date.fromisoformat(s)
    elif _isinstance(field, (django.db.models.FloatField,)):
        return float(s)
    elif _isinstance(
        field, (django.db.models.IntegerField, django.db.models.BigAutoField)
    ):
        return int(s)
    elif _isinstance(field, (django.db.models.BooleanField,)):
        return s and s != "0" and s != "False"
    return s


def gen_tab_action(
    table: str, action: str, fun: Callable, extra_context: Optional[Dict] = None
) -> path:
    """Generate a URL pattern for a table action."""
    return path(
        f"table/{table}/action/{action}/",
        fun,
        extra_context,
        name=f"tab_action_{table.lower()}_{action}",
    )


def gen_tab_field_action(
    table: str,
    field: str,
    action: str,
    fun: Callable,
    extra_context: Optional[Dict] = None,
) -> path:
    """Generate a URL pattern for a table field action."""
    return path(
        f"table/{table}/<int:parent_pk>/{field}/action/{action}/",
        fun,
        extra_context,
    )


def gen_row_action(
    table: str, action: str, fun: Callable, extra_context: Optional[Dict] = None
) -> path:
    """Generate a URL pattern for a row action."""
    return path(
        f"table/{table}/<int:pk>/action/{action}/",
        fun,
        extra_context,
        name=f"row_action_{table.lower()}_{action}",
    )


def transform_extra_context(context1: Dict, context2: Optional[Dict]) -> Dict:
    """Merge two context dictionaries, evaluating callables in context2."""
    if context2:
        for key, value in context2.items():
            context1[key] = value() if callable(value) else value
    return context1


def save(obj: Any, request: Any, view_type: str, param: Optional[Dict] = None) -> None:
    """Save an object, optionally using a custom save method."""
    if hasattr(obj, "save_from_request"):
        obj.save_from_request(request, view_type, param)
    else:
        obj.save()


def view_editor(
    request: Any,
    pk: int,
    app: str,
    tab: str,
    model: Any,
    template_name: str,
    field_edit_name: str,
    post_save_redirect: str,
    ext: str = "py",
    extra_context: Optional[Dict] = None,
    target: Optional[str] = None,
    parent_pk: int = 0,
    field_name: Optional[str] = None,
) -> HttpResponse:
    """Handle editor view for a model field."""
    if request.method == "POST":
        if target == "editable":
            value = request.POST["value"]
            pk = request.POST["pk"]
            obj = model.objects.get(id=pk)

            if (
                obj
                and hasattr(settings, "CANCAN")
                and is_in_cancan_rules(type(obj), request.ability.access_rules.rules)
            ):
                if not request.ability.can(f"editor_{field_edit_name}", obj):
                    return default_block(request)

            setattr(obj, field_edit_name, value)
            obj.save()
            return HttpResponse("OK")
        else:
            data = request.POST["data"]
            buf = data.replace("\r\n", "\n")
            obj = model.objects.get(id=pk)

            if (
                obj
                and hasattr(settings, "CANCAN")
                and is_in_cancan_rules(type(obj), request.ability.access_rules.rules)
            ):
                if not request.ability.can(f"editor_{field_edit_name}", obj):
                    return default_block(request)

            if "fragment" in request.GET:
                buf2 = getattr(obj, field_edit_name) or ""
                if request.GET["fragment"] == "header":
                    if "$$$" in buf2:
                        buf = f"{buf}$$${buf2.split('$$$')[1]}"
                elif request.GET["fragment"] == "footer":
                    buf = f"{buf2.split('$$$')[0]}$$${buf}"
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
            if not request.ability.can(f"editor_{field_edit_name}", obj):
                return default_block(request)

        table_name = model._meta.object_name
        txt = getattr(obj, field_edit_name) or ""

        if "fragment" in request.GET:
            if request.GET["fragment"] == "header":
                txt = txt.split("$$$")[0]
            elif request.GET["fragment"] == "footer":
                txt = txt.split("$$$")[1] if "$$$" in txt else ""

        f = next(
            (field for field in obj._meta.fields if field.name == field_edit_name), None
        )

        x = request.get_full_path().split("?", 1)
        get_param = f"?{x[1]}" if len(x) > 1 else ""

        if field_name:
            save_path = f"{app}/table/{tab}/{parent_pk}/{table_name}/{pk}/{field_edit_name}/py/editor/{get_param}"
        else:
            save_path = (
                f"{app}/table/{table_name}/{pk}/{field_edit_name}/py/editor/{get_param}"
            )

        if not txt and hasattr(obj, f"get_{field_edit_name}_if_empty"):
            txt = getattr(obj, f"get_{field_edit_name}_if_empty")(
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
            "verbose_field_name": f.verbose_name if f else "",
        }

        t = (
            obj.template_for_object(view_editor, c, ext)
            if hasattr(obj, "template_for_object")
            else None
        )
        t = t or "schsys/db_field_edt.html"

        return render_to_response(t, context=c, request=request)


class GenericTable:
    """GenericTable class for handling URL patterns and views."""

    def __init__(self, urlpatterns: Any, app: str, views_module: Optional[Any] = None):
        """Initialize GenericTable."""
        self.urlpatterns = urlpatterns
        self.app = app
        self.base_url = get_script_prefix()
        self.views_module = views_module

    def new_rows(
        self,
        tab: str,
        field: Optional[str] = None,
        title: str = "",
        title_plural: str = "",
        template_name: Optional[str] = None,
        extra_context: Optional[Dict] = None,
        queryset: Optional[Any] = None,
        prefix: Optional[str] = None,
    ) -> "GenericRows":
        """Create a new GenericRows instance."""
        rows = GenericRows(self, prefix, title, title_plural)
        rows.tab = tab
        if field:
            rows.set_field(field)
        rows.extra_context = extra_context
        rows.base_path = f"table/{tab}/"
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
                    f = getattr(m, field).related
                except AttributeError:
                    f = getattr(m, field).rel
                table_name = f.name if hasattr(f, "name") else f.var_name
            else:
                table_name = tab.lower()
            if ":" in table_name:
                rows.template_name = (
                    f"{self.app.lower()}/{table_name.split(':')[-1]}.html"
                )
            else:
                rows.template_name = f"{self.app.lower()}/{table_name}.html"
        if "." in tab:
            rows.base_model = apps.get_model(tab)
        else:
            rows.base_model = apps.get_model(f"{self.app}.{tab}")
        rows.queryset = queryset
        if "." in tab:
            pos = tab.rfind(".")
            rows.base_perm = f"{tab[:pos]}.%s_{tab[pos + 1 :].lower()}"
        else:
            rows.base_perm = f"{self.app}.%s_{tab.lower()}"
        return rows

    def append_from_schema(self, rows: "GenericRows", schema: str) -> None:
        """Append actions to rows based on a schema."""
        for char in schema.split(";"):
            if hasattr(rows, char):
                getattr(rows, char)()

    def from_schema(
        self,
        schema: str,
        tab: str,
        field: Optional[str] = None,
        title: str = "",
        title_plural: str = "",
        template_name: Optional[str] = None,
        extra_context: Optional[Dict] = None,
        queryset: Optional[Any] = None,
        prefix: Optional[str] = None,
    ) -> "GenericRows":
        """Create a GenericRows instance from a schema."""
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
        tab: str,
        title: str = "",
        title_plural: str = "",
        template_name: Optional[str] = None,
        extra_context: Optional[Dict] = None,
        queryset: Optional[Any] = None,
        prefix: Optional[str] = None,
    ) -> "GenericRows":
        """Create a standard set of views for a table."""
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
        tab: str,
        field: str,
        title: str = "",
        title_plural: str = "",
        template_name: Optional[str] = None,
        extra_context: Optional[Dict] = None,
        queryset: Optional[Any] = None,
        prefix: Optional[str] = None,
    ) -> "GenericRows":
        """Create views for a specific field in a table."""
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
        tab: str,
        title: str = "",
        title_plural: str = "",
        template_name: Optional[str] = None,
        extra_context: Optional[Dict] = None,
        queryset: Optional[Any] = None,
        prefix: Optional[str] = None,
    ) -> None:
        """Create tree views for a table."""
        return None


class GenericRows:
    """GenericRows class for handling rows in a table."""

    def __init__(
        self,
        table: GenericTable,
        prefix: Optional[str],
        title: str = "",
        title_plural: str = "",
        parent_rows: Optional["GenericRows"] = None,
    ):
        """Initialize GenericRows."""
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

    def _get_base_path(self) -> str:
        """Get the base path for URL patterns."""
        if self.field:
            if self.prefix:
                return fr"{self.base_path[:-1]}_{self.prefix}/(?P<parent_pk>-?\d+)/{self.field}/"
            return fr"{self.base_path}(?P<parent_pk>-?\d+)/{self.field}/"
        if self.prefix:
            return f"{self.base_path[:-1]}_{self.prefix}/"
        return self.base_path

    def table_paths_to_context(self, view_class: Any, context: Dict) -> None:
        """Add table paths to the context."""
        x = view_class.request.path.split("/table/", 1)
        x2 = x[1].split("/")

        bf = 0
        if (
            "base_filter" in view_class.kwargs
            and view_class.kwargs["base_filter"] is not None
        ):
            bf = 1

        if "parent_pk" in view_class.kwargs:
            context["table_path"] = f"{x[0]}/table/{'/'.join(x2[:3])}/"
            context["table_path_and_base_filter"] = (
                f"{x[0]}/table/{'/'.join(x2[: 3 + bf])}/"
            )
            context["table_path_and_filter"] = f"{x[0]}/table/{'/'.join(x2[:-3])}/"
        else:
            context["table_path"] = f"{x[0]}/table/{x2[0]}/"
            context["table_path_and_base_filter"] = (
                f"{context['table_path']}{x2[1]}/" if bf else context["table_path"]
            )
            context["table_path_and_filter"] = f"{x[0]}/table/{'/'.join(x2[:-3])}/"

    def set_field(self, field: Optional[str] = None) -> "GenericRows":
        """Set the field for the rows."""
        self.field = field
        return self

    def _append(
        self, url_str: str, fun: Callable, parm: Optional[Dict] = None
    ) -> "GenericRows":
        """Append a URL pattern to the urlpatterns."""
        if parm:
            self.table.urlpatterns.append(
                re_path(self._get_base_path() + url_str, fun, parm)
            )
        else:
            self.table.urlpatterns.append(re_path(self._get_base_path() + url_str, fun))
        return self

    def gen(self) -> "GenericRows":
        """Generate the URL patterns."""
        return self

    def list(self) -> "GenericRows":
        """
        Generate URL patterns for the list view.

        This function generates URL patterns for the list view with the following
        format:
            <base_path>/<filter>/<target>/<vtype>/
        where:
            <base_path> is the value of the base_path attribute of the GenericRows
                object;
            <filter> is the value of the filter attribute of the GenericRows object
                or the value of the base_filter keyword argument if it is provided;
            <target> is the value of the target keyword argument;
            <vtype> is the value of the vtype keyword argument.

        The function also registers the view in the VIEWS_REGISTER dictionary.

        Returns:
            self
        """
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

            def _context_for_tree(self) -> Dict:
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
                except:  # (ValueError, self.model.DoesNotExist):
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

            def doc_type(self) -> str:
                for doc_type in DOC_TYPES:
                    if self.kwargs["target"].startswith(doc_type):
                        return doc_type
                if "json" in self.request.GET and self.request.GET["json"] == "1":
                    return "json"
                return "html"

            def get_template_names(self) -> List[str]:
                names = super().get_template_names()
                if "target" in self.kwargs and "__" in self.kwargs["target"]:
                    target2 = self.kwargs["target"].split("__", 1)[1]
                    if "__" in target2:
                        app, t = target2.split("__")
                        names.insert(
                            0,
                            f"{app}/{self.template_name.split('/')[-1].replace('.html', t + '.html')}",
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
                        template2 = f"{x[0]}/{y[-1].replace('.html', x[1] + '.html')}"
                    else:
                        template2 = self.template_name.replace(".html", v + ".html")
                    names.insert(0, template2)
                return names

            def get_paginate_by(self, queryset: Any) -> Optional[int]:
                if self.doc_type() in DOC_TYPES and self.doc_type() != "json":
                    return None
                return self.paginate_by

            def get(self, request: Any, *args: Any, **kwargs: Any) -> HttpResponse:
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

            def post(self, request: Any, *args: Any, **kwargs: Any) -> HttpResponse:
                return self.get(request, *args, **kwargs)

            def get_context_data(self, **kwargs: Any) -> Dict:
                nonlocal parent_class
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

            def get_queryset(self) -> Any:
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
                            if hasattr(settings, "CANCAN") and is_in_cancan_rules(
                                self.model, self.request.ability.access_rules.rules
                            ):
                                ret = self.request.ability.queryset_for(
                                    "view", self.model
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

        VIEWS_REGISTER["list"][self.base_model] = ListView

        fun = make_perms_test_fun(
            parent_class.table.app,
            self.base_model,
            self.base_perm % "list",
            ListView.as_view(),
        )
        self._append(url, fun)

        return self

    def detail(self) -> "GenericRows":
        """
        Generate a detail view for a specific element.

        The detail view allows the user to view detailed information about an element
        of the table. It is accessible to users with the "view" permission on the table.

        :return: The detail view as a class.
        :rtype: generic.DetailView
        """

        url = r"(?P<pk>\d+)/(?P<target>[\w_]*)/(?P<vtype>view|row_action)/$"
        parent_class = self

        class DetailView(generic.DetailView):
            queryset = self.queryset

            if self.field:
                try:
                    f = getattr(self.base_model, self.field).related
                except AttributeError:
                    f = getattr(self.base_model, self.field).rel
                model = f.related_model
            else:
                model = self.base_model

            template_name = self.template_name
            title = self.title
            response_class = ExtTemplateResponse

            def get_object(self, queryset: Optional[Any] = None) -> Any:
                obj = super().get_object(queryset)
                if hasattr(obj, "get_derived_object"):
                    obj2 = obj.get_derived_object({"view": self})
                    self.model = type(obj2)
                    return obj2
                return obj

            def doc_type(self) -> str:
                for doc_type in DOC_TYPES:
                    if self.kwargs["target"].startswith(doc_type):
                        return doc_type
                if "json" in self.request.GET and self.request.GET["json"] == "1":
                    return "json"
                return "html"

            def get_template_names(self) -> List[str]:
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
                        template2 = f"{x[0]}/{y[-1].replace('.html', x[1] + '.html')}"
                    else:
                        template2 = self.template_name.replace(".html", v + ".html")
                    names.insert(0, template2)
                return names

            def get_context_data(self, **kwargs: Any) -> Dict:
                nonlocal parent_class
                context = super().get_context_data(**kwargs)
                context["view"] = self
                context["title"] = f"{self.title} - {str(_('element information'))}"
                if "version" in self.request.GET:
                    context["version"] = self.request.GET["version"]

                parent_class.table_paths_to_context(self, context)

                return context

            def get(self, request: Any, *args: Any, **kwargs: Any) -> HttpResponse:
                self.object = self.get_object()

                if (
                    self.object
                    and hasattr(settings, "CANCAN")
                    and is_in_cancan_rules(
                        type(self.object), request.ability.access_rules.rules
                    )
                ):
                    if not request.ability.can("detail", self.object):
                        return default_block(request)

                if self.kwargs["vtype"] == "row_action":
                    if hasattr(self.object, "row_action"):
                        ret = getattr(self.model, "row_action")(
                            self.model, request, args, kwargs
                        )
                        if ret is None:
                            raise Http404("Action doesn't exists")
                        return JsonResponse(ret)
                    raise Http404("Action doesn't exists")

                return super().get(request, *args, **kwargs)

            def post(self, request: Any, *args: Any, **kwargs: Any) -> HttpResponse:
                return self.get(request, *args, **kwargs)

        VIEWS_REGISTER["detail"][self.base_model] = DetailView

        fun = make_perms_test_fun(
            parent_class.table.app,
            self.base_model,
            self.base_perm % "view",
            DetailView.as_view(),
        )
        return self._append(url, fun)

    def edit(self) -> "GenericRows":
        """
        Generate an edit view.

        The edit view allows the user to modify an existing element of the
        table. The view is accessible to users with the "change" permission on
        the table.

        :return: The edit view as a class.
        :rtype: generic.UpdateView
        """
        url = r"(?P<pk>\d+)/edit/$"
        parent_class = self

        class UpdateView(generic.UpdateView):
            # doc_type = "html"
            response_class = ExtTemplateResponse

            if self.field:
                try:
                    f = getattr(self.base_model, self.field).related
                except AttributeError:
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
        """
        Add a new element to the table.

        URL: /table/<app>/<model>/add/<add_param>/
        URL parameters:
            - add_param: optional parameter used to initialize the form
        """
        url = r"(?P<add_param>[\w=_-]*)/add/$"
        parent_class = self

        class CreateView(generic.CreateView):
            response_class = ExtTemplateResponse
            if self.field and self.field != "this":
                try:
                    f = getattr(self.base_model, self.field).related
                except AttributeError:
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
                            except self.pmodel.DoesNotExist:
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
                                except self.pmodel.DoesNotExist:
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
                        if hasattr(self.object, pos) and pos not in p:
                            try:
                                setattr(self.object, pos, self.init_form[pos])
                            except self.pmodel.DoesNotExist:
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
        """
        Generate a delete view.

        This method sets up a delete view that allows users with the appropriate
        permissions to delete an element from the table. The view is registered
        with the appropriate URL pattern and permissions are checked before allowing
        the delete operation.

        The DeleteView class provides methods to handle GET and POST requests,
        ensuring that the user has the necessary permissions and performing any
        additional actions needed during the delete operation.

        The view is accessible via the URL pattern: /<pk>/delete/

        :return: The delete view as a class.
        :rtype: generic.DeleteView
        """

        url = r"(?P<pk>\d+)/delete/$"
        parent_class = self

        class DeleteView(generic.DeleteView):
            response_class = LocalizationTemplateResponse
            if self.field:
                try:
                    f = getattr(self.base_model, self.field).related
                except AttributeError:
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
        """
        Generate URL patterns for the editor view.

        The editor view allows the user to edit specific fields of an element.
        The view is accessible to users with the "change" permission on the table.

        The URL pattern is as follows:
            /table/<app>/<model>/<pk>/<field_edit_name>/<target>/editor/

        :return: The URL pattern as a string.
        :rtype: str
        """
        url = r"(?P<pk>\d+)/(?P<field_edit_name>[\w_]*)/(?P<target>[\w_]*)/editor/$"
        fun = make_perms_test_fun(
            self.table.app, self.base_model, self.base_perm % "change", view_editor
        )
        if self.field:
            try:
                f = getattr(self.base_model, self.field).related
            except AttributeError:
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
    """
    Generate generic table urls

    Args:
        urlpatterns - urlpatterns object defined in urls.py
        app - application name
        tab - table name
        title - title of the table (default: '')
        title_plural - plural title of the table (default: '')
        template_name - template name (default: None)
        extra_context - extra context (default: None)
        queryset - queryset (default: None)
        views_module - views module (default: None)

    Returns:
        None
    """
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
    """
    Extend a generic view by replacing an existing method with a new method.

    Args:
        view_name (str): The name of the view to be extended.
        model (str): The model associated with the view.
        method_name (str): The name of the method to be replaced.
        new_method (Callable): The new method to replace the existing one.

    The function updates the specified method of the class retrieved from
    VIEWS_REGISTER with the new method. It also archives the old method
    under a new attribute name prefixed with "old_" if the old method exists.
    """

    try:
        cls = VIEWS_REGISTER[view_name][model]
    except KeyError:
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
