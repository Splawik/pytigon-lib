"""Template variant mixin for schviews generic views."""

from django.conf import settings


class TemplateVariantMixin:
    """Mixin that resolves template variants based on URL kwargs and GET params.

    Supports two mechanisms:
    - ``target`` kwarg prefixed with ``ver`` selects a version template.
    - ``version`` GET parameter allows client-controlled template selection.

    ``version`` supports cross-app templates via ``app__suffix`` notation
    when ``settings.SKIP_APPS_PREFIXES`` contains that app prefix.
    """

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
                template2 = f"{x[0]}/{y[-1].replace('.html', x[1] + '.html')}"
            else:
                template2 = self.template_name.replace(".html", v + ".html")
            names.insert(0, template2)
        return names


class TemplateVariantListViewMixin(TemplateVariantMixin):
    """Template variant mixin for ListView with extended target handling.

    In addition to the base TemplateVariantMixin behaviour, this mixin
    supports ``__``-separated target namespaces (e.g. ``target__app__suffix``).
    """

    def get_template_names(self):
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
