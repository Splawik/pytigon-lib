"""DeleteView for schviews generic views."""

from django.utils.translation import gettext_lazy as _
from django.views import generic

from pytigon_lib.schviews.actions import delete_row_ok
from pytigon_lib.schviews.schrules import is_rules_active, user_can

from .._utils import make_path_lazy
from ..derived import DerivedObjectMixin
from ..mixins import TemplateVariantMixin
from ..perms import default_block
from ..viewtools import LocalizationTemplateResponse


def _create_delete_view(parent_rows):
    url = r"(?P<pk>\d+)/delete/$"

    if parent_rows.field:
        try:
            f = getattr(parent_rows.base_model, parent_rows.field).related
        except AttributeError:
            f = getattr(parent_rows.base_model, parent_rows.field).rel
        _model = f.related_model
    else:
        _model = parent_rows.base_model

    class DeleteView(
        TemplateVariantMixin, DerivedObjectMixin, generic.DeleteView
    ):
        response_class = LocalizationTemplateResponse
        model = _model
        success_url = make_path_lazy("ok")
        template_name = parent_rows.template_name
        title = parent_rows.title

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            context["view"] = self
            context["title"] = self.title + " - " + str(_("delete element"))
            if "version" in self.request.GET:
                context["version"] = self.request.GET["version"]

            parent_rows.table_paths_to_context(self, context)

            return context

        def get(self, request, *args, **kwargs):
            self.object = self.get_object(self.queryset)
            if self.object and is_rules_active():
                if not user_can(
                    self.request.user, "delete", type(self.object), self.object
                ):
                    return default_block(request)

            return super().get(request, *args, **kwargs)

        def post(self, request, *args, **kwargs):
            self.object = self.get_object(self.queryset)
            if self.object and is_rules_active():
                if not user_can(
                    self.request.user, "delete", type(self.object), self.object
                ):
                    return default_block(request)

            if hasattr(self.object, "on_delete"):
                self.object.on_delete(request, self)

            pk = int(self.object.id)

            super().post(request, *args, **kwargs)

            return delete_row_ok(request, pk, self.object)

    return url, DeleteView
