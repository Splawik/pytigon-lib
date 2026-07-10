"""UpdateView for schviews generic views."""

import logging

from django.http import HttpResponseRedirect
from django.utils.translation import gettext_lazy as _
from django.views import generic

from pytigon_lib.schviews.actions import update_row_ok
from pytigon_lib.schviews.schrules import is_rules_active, user_can

from .._utils import make_path_lazy, save
from ..derived import DerivedObjectMixin
from ..mixins import TemplateVariantMixin
from ..perms import default_block
from ..viewtools import ExtTemplateResponse

logger = logging.getLogger(__name__)


def _create_update_view(parent_rows):
    url = r"(?P<pk>\d+)/edit/$"

    if parent_rows.field:
        try:
            f = getattr(parent_rows.base_model, parent_rows.field).related
        except AttributeError:
            f = getattr(parent_rows.base_model, parent_rows.field).rel
        _model = f.related_model
    else:
        _model = parent_rows.base_model

    class UpdateView(
        TemplateVariantMixin, DerivedObjectMixin, generic.UpdateView
    ):
        response_class = ExtTemplateResponse
        model = _model
        success_url = make_path_lazy("ok")
        template_name = parent_rows.template_name
        title = parent_rows.title
        fields = "__all__"

        def doc_type(self):
            return "html"

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            context["view"] = self
            context["title"] = self.title + " - " + str(_("update element"))
            if "version" in self.request.GET:
                context["version"] = self.request.GET["version"]

            parent_rows.table_paths_to_context(self, context)

            return context

        def get(self, request, *args, **kwargs):
            self.object = self.get_object()

            if self.object and is_rules_active():
                if not user_can(
                    self.request.user, "change", type(self.object), self.object
                ):
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

            if self.object and is_rules_active():
                if not user_can(
                    self.request.user, "change", type(self.object), self.object
                ):
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
                logger.warning("Edit form invalid: %s", form.errors)
                return self.form_invalid(form)

        def form_valid(self, form, request=None):
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

    return url, UpdateView
