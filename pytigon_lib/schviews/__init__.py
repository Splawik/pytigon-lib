"""
Generic views and URL-pattern helpers for the schviews module.

Provides base classes (:class:`GenericTable`, :class:`GenericRows`) that
generate Django URL patterns and class-based views for common CRUD
operations on database tables.  Also includes standalone utility
functions for URL generation, value conversion, and editor views.

Classes:
    GenericTable:
        Entry point for building URL patterns and views for a database table.

    GenericRows:
        Represents a set of CRUD views for a specific table (or a field
        of a table).  Methods like ``list()``, ``detail()``, ``edit()``,
        ``add()``, ``delete()``, ``editor()`` append corresponding URL
        patterns.

Functions:
    make_path / make_path_lazy:
        Generate a URL path from a Django view name.

    convert_str_to_model_field:
        Convert a string value to the appropriate Python type for a Django
        model field.

    transform_extra_context:
        Merge two context dictionaries, calling callables in the second.

    save:
        Persist an object, respecting ``save_from_request`` if available.

    view_editor:
        Handle inline editing of a single model field.

    gen_tab_action / gen_tab_field_action / gen_row_action:
        Generate individual URL patterns for table-/row-level actions.

    generic_table / generic_table_start:
        Convenience entry points for building complete table view sets.

    extend_generic_view:
        Monkey-patch a method on a registered generic view class.
"""

import logging
import threading
from collections.abc import Callable
from typing import Any, Optional

from django.apps import apps
from django.http import Http404, HttpResponse, HttpResponseRedirect, JsonResponse
from django.urls import get_script_prefix, path, re_path
from django.utils.translation import gettext_lazy as _

from pytigon_lib.schtools.schjson import json_loads
from pytigon_lib.schviews.schrules import (
    is_rules_active,
    user_can,
)
from pytigon_lib.schviews.viewtools import render_to_response

from ._utils import (
    convert_str_to_model_field,
    make_path,
    make_path_lazy,
    save,
    transform_extra_context,
)
from .perms import default_block, make_perms_test_fun
from .views import (
    _create_create_view,
    _create_delete_view,
    _create_detail_view,
    _create_list_view,
    _create_update_view,
)

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Module-level registry of generated view classes, keyed by
# (view_type, model).  Other parts of the framework can look up or
# replace view classes via ``extend_generic_view``.
# --------------------------------------------------------------------------
VIEWS_REGISTER: dict[str, dict[Any, Any]] = {
    "list": {},
    "detail": {},
    "edit": {},
    "create": {},
    "delete": {},
}

_VIEWS_REGISTER_LOCK = threading.Lock()


# --------------------------------------------------------------------------
# URL-pattern generators (actions)
# --------------------------------------------------------------------------
# Inline field editor
# --------------------------------------------------------------------------


def gen_tab_action(
    table: str, action: str, fun: Callable, extra_context: dict | None = None
) -> path:
    """Generate a URL pattern for a table action.

    Args:
        table: Table name.
        action: Action identifier.
        fun: The view function or class-based view ``as_view()`` result.
        extra_context: Optional extra context dictionary for the view.

    Returns:
        A Django ``path`` object.
    """
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
    extra_context: dict | None = None,
) -> path:
    """Generate a URL pattern for a table field action.

    Args:
        table: Table name.
        field: Field name.
        action: Action identifier.
        fun: The view function or class-based view ``as_view()`` result.
        extra_context: Optional extra context dictionary.

    Returns:
        A Django ``path`` object.
    """
    return path(
        f"table/{table}/<int:parent_pk>/{field}/action/{action}/",
        fun,
        extra_context,
    )


def gen_row_action(
    table: str, action: str, fun: Callable, extra_context: dict | None = None
) -> path:
    """Generate a URL pattern for a row action.

    Args:
        table: Table name.
        action: Action identifier.
        fun: The view function or class-based view ``as_view()`` result.
        extra_context: Optional extra context dictionary.

    Returns:
        A Django ``path`` object.
    """
    return path(
        f"table/{table}/<int:pk>/action/{action}/",
        fun,
        extra_context,
        name=f"row_action_{table.lower()}_{action}",
    )


# ==========================================================================
# Inline field editor
# ==========================================================================


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
    extra_context: dict | None = None,
    target: str | None = None,
    parent_pk: int = 0,
    field_name: str | None = None,
) -> HttpResponse:
    """Handle inline editing of a single model field.

    Depending on the *target* parameter, the editor behaves as a simple
    inline-editable widget or as a full-page code/text editor with
    fragment support (using ``$$$`` as fragment separator).

    django-rules permission checks are performed when the rules engine is
    active.

    Args:
        request: The current HTTP request.
        pk: Primary key of the object to edit.
        app: Application label.
        tab: Table name.
        model: Django model class.
        template_name: Default template for the editor page.
        field_edit_name: Name of the field being edited.
        post_save_redirect: Redirect URL after save (unused here but
            required by caller convention).
        ext: Extension/syntax identifier for the editor (default ``"py"``).
        extra_context: Optional extra context for the template.
        target: Editor mode (``"editable"`` for inline, otherwise full
            page).
        parent_pk: Optional parent primary key for field-scoped URLs.
        field_name: Optional field name for URL construction.

    Returns:
        An ``HttpResponse`` (``"OK"`` for POST, editor page for GET).
    """
    if request.method == "POST":
        if target == "editable":
            value = request.POST["value"]
            pk = request.POST["pk"]
            obj = model.objects.get(id=pk)

            if obj and is_rules_active():
                if not user_can(
                    request.user, f"editor_{field_edit_name}", type(obj), obj
                ):
                    return default_block(request)

            setattr(obj, field_edit_name, value)
            obj.save()
            return HttpResponse("OK")
        else:
            data = request.POST["data"]
            buf = data.replace("\r\n", "\n")
            obj = model.objects.get(id=pk)

            if obj and is_rules_active():
                if not user_can(
                    request.user, f"editor_{field_edit_name}", type(obj), obj
                ):
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

        if obj and is_rules_active():
            if not user_can(request.user, f"editor_{field_edit_name}", type(obj), obj):
                return default_block(request)

        table_name = model._meta.object_name
        txt = getattr(obj, field_edit_name) or ""

        if "fragment" in request.GET:
            if request.GET["fragment"] == "header":
                txt = txt.split("$$$")[0]
            elif request.GET["fragment"] == "footer":
                txt = txt.split("$$$")[1] if "$$$" in txt else ""

        f = next(
            (fld for fld in obj._meta.fields if fld.name == field_edit_name),
            None,
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

    def __init__(self, urlpatterns: Any, app: str, views_module: Any | None = None):
        """Initialize GenericTable."""
        self.urlpatterns = urlpatterns
        self.app = app
        self.base_url = get_script_prefix()
        self.views_module = views_module

    def new_rows(
        self,
        tab: str,
        field: str | None = None,
        title: str = "",
        title_plural: str = "",
        template_name: str | None = None,
        extra_context: dict | None = None,
        queryset: Any | None = None,
        prefix: str | None = None,
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
        field: str | None = None,
        title: str = "",
        title_plural: str = "",
        template_name: str | None = None,
        extra_context: dict | None = None,
        queryset: Any | None = None,
        prefix: str | None = None,
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
        template_name: str | None = None,
        extra_context: dict | None = None,
        queryset: Any | None = None,
        prefix: str | None = None,
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
        template_name: str | None = None,
        extra_context: dict | None = None,
        queryset: Any | None = None,
        prefix: str | None = None,
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



class GenericRows:
    """GenericRows class for handling rows in a table."""

    def __init__(
        self,
        table: GenericTable,
        prefix: str | None,
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
                return rf"{self.base_path[:-1]}_{self.prefix}/(?P<parent_pk>-?\d+)/{self.field}/"
            return rf"{self.base_path}(?P<parent_pk>-?\d+)/{self.field}/"
        if self.prefix:
            return f"{self.base_path[:-1]}_{self.prefix}/"
        return self.base_path

    def table_paths_to_context(self, view_class: Any, context: dict) -> None:
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

    def set_field(self, field: str | None = None) -> "GenericRows":
        """Set the field for the rows."""
        self.field = field
        return self

    def _append(
        self, url_str: str, fun: Callable, parm: dict | None = None
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
        url, ListView = _create_list_view(self)

        VIEWS_REGISTER["list"][self.base_model] = ListView

        fun = make_perms_test_fun(
            self.table.app,
            self.base_model,
            self.base_perm % "list",
            ListView.as_view(),
        )
        self._append(url, fun)

        return self

    def detail(self) -> "GenericRows":
        url, DetailView = _create_detail_view(self)

        VIEWS_REGISTER["detail"][self.base_model] = DetailView

        fun = make_perms_test_fun(
            self.table.app,
            self.base_model,
            self.base_perm % "view",
            DetailView.as_view(),
        )
        return self._append(url, fun)

    def edit(self) -> "GenericRows":
        url, UpdateView = _create_update_view(self)

        VIEWS_REGISTER["edit"][self.base_model] = UpdateView

        fun = make_perms_test_fun(
            self.table.app,
            self.base_model,
            self.base_perm % "change",
            UpdateView.as_view(),
        )
        return self._append(url, fun)

    def add(self):
        url, CreateView = _create_create_view(self)

        VIEWS_REGISTER["create"][self.base_model] = CreateView

        fun = make_perms_test_fun(
            self.table.app,
            self.base_model,
            self.base_perm % "add",
            CreateView.as_view(),
        )
        return self._append(url, fun)

    def delete(self):
        url, DeleteView = _create_delete_view(self)

        VIEWS_REGISTER["delete"][self.base_model] = DeleteView

        fun = make_perms_test_fun(
            self.table.app,
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
    """Extend a generic view by replacing an existing method with a new method.

    The old method is archived under ``"old_<method_name>"`` as a list so
    that multiple extensions can be stacked.

    Args:
        view_name: The view type key in ``VIEWS_REGISTER``
            (e.g. ``"list"``, ``"edit"``).
        model: The model class registered for this view.
        method_name: The name of the method to replace.
        new_method: The replacement callable.

    Returns:
        ``None`` if the view or model was not found.
    """

    try:
        cls = VIEWS_REGISTER[view_name][model]
    except KeyError:
        logger.debug(
            "extend_generic_view: view '%s' / model '%s' not found.",
            view_name,
            model,
        )
        return None
    if cls:
        old_method = getattr(cls, method_name, None)
        setattr(cls, method_name, new_method)
        if old_method is not None:
            arch_method_name = "old_" + method_name
            arch_list = getattr(cls, arch_method_name, None)
            if arch_list is not None:
                arch_list.append(old_method)
            else:
                setattr(cls, arch_method_name, [old_method])
