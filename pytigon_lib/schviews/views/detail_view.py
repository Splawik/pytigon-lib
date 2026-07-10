"""DetailView for schviews generic views."""

from django.http import Http404, HttpResponse, JsonResponse
from django.utils.translation import gettext_lazy as _
from django.views import generic

from pytigon_lib.schviews.schrules import is_rules_active, user_can
from pytigon_lib.schviews.viewtools import DOC_TYPES, ExtTemplateResponse

from ..derived import DerivedObjectMixin
from ..mixins import TemplateVariantMixin
from ..perms import default_block


def _create_detail_view(parent_rows):
    url = r"(?P<pk>\d+)/(?P<target>[\w_]*)/(?P<vtype>view|row_action)/$"

    if parent_rows.field:
        try:
            f = getattr(parent_rows.base_model, parent_rows.field).related
        except AttributeError:
            f = getattr(parent_rows.base_model, parent_rows.field).rel
        _model = f.related_model
    else:
        _model = parent_rows.base_model

    class DetailView(
        TemplateVariantMixin, DerivedObjectMixin, generic.DetailView
    ):
        queryset = parent_rows.queryset
        model = _model
        template_name = parent_rows.template_name
        title = parent_rows.title
        response_class = ExtTemplateResponse

        def doc_type(self):
            for doc_type in DOC_TYPES:
                if self.kwargs["target"].startswith(doc_type):
                    return doc_type
            if "json" in self.request.GET and self.request.GET["json"] == "1":
                return "json"
            return "html"

        def get_context_data(self, **kwargs):
            context = super().get_context_data(**kwargs)
            context["view"] = self
            context["title"] = f"{self.title} - {_('element information')!s}"
            if "version" in self.request.GET:
                context["version"] = self.request.GET["version"]

            parent_rows.table_paths_to_context(self, context)

            return context

        def get(self, request, *args, **kwargs):
            self.object = self.get_object()

            if self.object and is_rules_active():
                if not user_can(
                    request.user, "detail", type(self.object), self.object
                ):
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

        def post(self, request, *args, **kwargs):
            return self.get(request, *args, **kwargs)

    return url, DetailView
