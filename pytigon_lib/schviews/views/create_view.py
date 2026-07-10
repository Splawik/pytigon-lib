"""CreateView for schviews generic views."""

import logging

from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.views import generic

from pytigon_lib.schviews.actions import new_row_ok
from pytigon_lib.schviews.schrules import is_rules_active, user_can

from .._utils import (
    convert_str_to_model_field,
    make_path_lazy,
    save,
    transform_extra_context,
)
from ..mixins import TemplateVariantMixin
from ..perms import default_block
from ..viewtools import ExtTemplateResponse

logger = logging.getLogger(__name__)


def _create_create_view(parent_rows):
    url = r"(?P<add_param>[\w=_-]*)/add/$"

    if parent_rows.field and parent_rows.field != "this":
        try:
            f = getattr(parent_rows.base_model, parent_rows.field).related
        except AttributeError:
            f = getattr(parent_rows.base_model, parent_rows.field).rel
        _model = f.related_model
        _pmodel = parent_rows.base_model
    else:
        _model = parent_rows.base_model
        _pmodel = _model

    class CreateView(
        TemplateVariantMixin, generic.CreateView
    ):
        response_class = ExtTemplateResponse
        model = _model
        pmodel = _pmodel
        template_name = parent_rows.template_name
        title = parent_rows.title
        field = parent_rows.field
        init_form = None
        fields = "__all__"

        def get_object(self, queryset=None):
            obj = self.model()
            if hasattr(obj, "get_derived_object"):
                obj2 = obj.get_derived_object({"view": self})
                self.model = type(obj2)
                return obj2
            return obj

        def doc_type(self):
            return "html"

        def get_success_url(self):
            return make_path_lazy("ok")

        def _get_form(self, request, *args, **kwargs):
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

            if self.object and is_rules_active():
                if not user_can(
                    self.request.user, "add", type(self.object), self.object
                ):
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

            if self.object and is_rules_active():
                if not user_can(
                    self.request.user, "add", type(self.object), self.object
                ):
                    return default_block(request)

            if self.model and hasattr(self.model, "is_form_valid"):

                def vfun():
                    return self.model.is_form_valid(form)

            else:
                vfun = form.is_valid
            if vfun():
                return self.form_valid(form, request)
            else:
                logger.warning("Add form invalid: %s", form.errors)
                return self.form_invalid(form)

        def get_initial(self):
            d = super().get_initial()

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
            ret = super().get_form_kwargs()
            if self.init_form:
                if "data" in ret:
                    data = ret["data"].copy()
                    for key, value in self.init_form.items():
                        if data.get(key):
                            continue
                        data[key] = value

                    ret.update({"data": data})

            return ret

        def form_valid(self, form, request=None):
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
                if self.request.GET.get("redirect"):
                    ctx = self.get_context_data(form=form)
                    tp = ctx["table_path"]
                    return HttpResponseRedirect(tp + f"{self.object.pk}/edit/")
                else:
                    return new_row_ok(request, int(self.object.id), self.object)
            else:
                return super(generic.edit.ModelFormMixin, self).form_valid(form)

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            context["view"] = self
            context["title"] = self.title + " - " + str(_("new element"))
            context["object"] = self.object
            context["add_param"] = self.kwargs["add_param"]
            if "version" in self.request.GET:
                context["version"] = self.request.GET["version"]

            parent_rows.table_paths_to_context(self, context)

            return context

    return url, CreateView
