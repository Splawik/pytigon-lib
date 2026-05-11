"""Utility functions and classes for template rendering, response generation,
and object manipulation in a Django web application.

Classes:
    LocalizationTemplateResponse:
        A TemplateResponse subclass that resolves templates based on the
        request's language code.

    ExtTemplateResponse:
        A LocalizationTemplateResponse subclass that handles rendering of
        various document types (PDF, ODF, OOXML, hdoc, hxls, JSON, TXT).

    ExtTemplateView:
        A generic.TemplateView subclass that uses ExtTemplateResponse for
        rendering and supports multiple output document types.

Functions:
    transform_template_name:
        Transforms the template name using an object's method if available.

    change_pos:
        Changes the position (ordering) of an object in a database table
        by swapping primary keys with an adjacent record.

    duplicate_row:
        Duplicates a given row in a database table (resets primary key).

    render_to_response:
        Renders a template with a given context and returns an HttpResponse.

    render_to_response_ext:
        Renders a template with a given context and document type, returns
        an HttpResponse.

    dict_to_template:
        Decorator that renders the returned dictionary as a template.

    dict_to_odf / dict_to_ooxml:
        Decorators that render the returned dictionary as ODF / OOXML.

    dict_to_txt / dict_to_hdoc / dict_to_hxls:
        Decorators that render the returned dictionary as TXT / HDOC / HXLS.

    dict_to_pdf / dict_to_spdf:
        Decorators that render the returned dictionary as PDF / SPDF.

    dict_to_json / dict_to_xml:
        Decorators that render the returned dictionary as JSON / XML.
"""

import functools
import io
import logging
import os
import os.path

from django.apps import apps
from django.core import serializers
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max, Min
from django.http import HttpResponse, HttpResponseRedirect
from django.template import Context, RequestContext, loader
from django.template.response import TemplateResponse
from django.views import generic

from pytigon_lib.schdjangoext.spreadsheet_render import render_odf, render_ooxml
from pytigon_lib.schdjangoext.tools import make_href
from pytigon_lib.schhtml.htmlviewer import stream_from_html
from pytigon_lib.schparser.html_parsers import SimpleTabParserBase
from pytigon_lib.schtools import schjson

LOGGER = logging.getLogger(__name__)

# Supported document types, ordered by priority for URL target matching.
DOC_TYPES = (
    "pdf",
    "spdf",
    "ods",
    "odt",
    "odp",
    "xlsx",
    "docx",
    "pptx",
    "txt",
    "json",
    "hdoc",
    "hxls",
)

# Mapping from doc_type to (suffix, system_template).
# Used by ExtTemplateResponse._build_template_list to avoid repetitive
# if/elif chains when constructing template name lists.
_DOC_TYPE_CONFIG = {
    "pdf": ("_pdf.html", "schsys/table_pdf.html"),
    "spdf": ("_spdf.html", "schsys/table_spdf.html"),
    "txt": ("_txt.html", None),
    "hdoc": ("_hdoc.html", None),
    "hxls": ("_hxls.html", None),
}

# OpenDocument format types that use render_odf() for output.
_ODF_TYPES = frozenset(("ods", "odt", "odp"))

# Office Open XML format types that use render_ooxml() for output.
_OOXML_TYPES = frozenset(("xlsx", "docx", "pptx"))

# HTML-based document types that use HtmlViewerParser for output.
_HDOC_TYPES = frozenset(("hdoc", "hxls"))

# PDF-like types that go through stream_from_html.
_PDF_TYPES = frozenset(("pdf", "spdf"))


def transform_template_name(obj, request, template_name):
    """Transform the template name using the object's method if available.

    If *obj* has a method ``transform_template_name``, it is called with the
    request and the original template name.  Otherwise the original template
    name is returned unchanged.

    Args:
        obj: Any object; inspected for ``transform_template_name``.
        request (HttpRequest): The current Django request.
        template_name (str): The original template name.

    Returns:
        str: The (possibly transformed) template name.
    """
    if hasattr(obj, "transform_template_name"):
        return obj.transform_template_name(request, template_name)
    return template_name


def change_pos(request, app, tab, pk, forward=True, field=None, callback_fun=None):
    """Swap the position of a record with its neighbour in a database table.

    The record identified by *pk* is swapped with the next or previous record
    (depending on *forward*) within the same table.  When *field* is given,
    only records sharing the same value for that foreign-key field are
    considered.

    **Important**: this swaps primary keys (``id``) between the two rows.
    This approach works for simple ordering but may not be appropriate for
    tables with many foreign-key references.

    Args:
        request (HttpRequest): The current Django request (unused in logic,
            but required by the caller convention).
        app (str): Django application label (e.g. ``"myapp"``).
        tab (str): Model class name (e.g. ``"MyModel"``).
        pk (int): Primary key of the record to move.
        forward (bool): If ``True``, move towards higher IDs; if ``False``,
            move towards lower IDs.  Defaults to ``True``.
        field (str | None): Optional name of a ForeignKey field.  When
            provided, only records pointing to the same related object are
            considered for the swap.
        callback_fun (callable | None): Optional callback invoked with the
            two swapped objects: ``callback_fun(obj, obj2)``.

    Returns:
        HttpResponse: A response whose body is ``"YES"`` (and a ``<meta>``
        tag triggering a page refresh) when the swap succeeded, or ``"NO"``
        when there is no adjacent record to swap with.
    """
    try:
        model = apps.get_model(app, tab)
        if model is None:
            LOGGER.error("change_pos: model %s.%s not found.", app, tab)
            return HttpResponse("NO")
        obj = model.objects.get(id=pk)
    except ObjectDoesNotExist:
        LOGGER.warning("change_pos: object %s.%s pk=%s not found.", app, tab, pk)
        return HttpResponse("NO")

    # Build the filtered queryset.
    if field:
        field_value = getattr(obj, field)
        if field_value is None:
            LOGGER.warning(
                "change_pos: field '%s' is None for object pk=%s.", field, pk
            )
            return HttpResponse("NO")
        query = model.objects.filter(**{field: field_value})
    else:
        query = model.objects.all()

    # Find the adjacent record.
    if forward:
        result = query.filter(id__gt=pk).order_by("id").aggregate(Min("id"))
        neighbour_id = result.get("id__min")
    else:
        result = query.filter(id__lt=pk).order_by("-id").aggregate(Max("id"))
        neighbour_id = result.get("id__max")

    if neighbour_id is None:
        return HttpResponse("NO")

    try:
        obj2 = model.objects.get(id=neighbour_id)
    except ObjectDoesNotExist:
        LOGGER.warning(
            "change_pos: neighbour object %s.%s pk=%s disappeared.",
            app,
            tab,
            neighbour_id,
        )
        return HttpResponse("NO")

    # Swap primary keys (preserved for backward compatibility).
    tmp_id = obj.id
    obj.id = obj2.id
    obj2.id = tmp_id

    if callback_fun:
        callback_fun(obj, obj2)

    obj.save()
    obj2.save()

    return HttpResponse(
        '<head><meta name="TARGET" content="refresh_page" /></head><body>YES</body>'
    )


def duplicate_row(request, app, tab, pk, field=None):
    """Duplicate a row in the database by resetting its primary key.

    The row identified by *pk* is loaded, its primary key is set to ``None``,
    and the record is saved as a new row.  The *field* and *request* arguments
    are accepted for API compatibility but are currently unused.

    Args:
        request (HttpRequest): The current Django request (unused).
        app (str): Django application label.
        tab (str): Model class name.
        pk (int): Primary key of the row to duplicate.
        field (str | None): Unused; accepted for call-site compatibility.

    Returns:
        HttpResponse: ``"YES"`` when the duplication succeeded, ``"NO"``
        when the source row was not found.
    """
    try:
        model = apps.get_model(app, tab)
        if model is None:
            LOGGER.error("duplicate_row: model %s.%s not found.", app, tab)
            return HttpResponse("NO")
        obj = model.objects.get(id=pk)
    except ObjectDoesNotExist:
        LOGGER.warning("duplicate_row: object %s.%s pk=%s not found.", app, tab, pk)
        return HttpResponse("NO")

    obj.id = None
    obj.save()
    return HttpResponse("YES")


class LocalizationTemplateResponse(TemplateResponse):
    """A TemplateResponse that resolves language-specific template variants.

    When the request carries a ``LANGUAGE_CODE`` other than ``"en"``, the
    resolver first looks for a template whose name includes the language
    suffix (e.g. ``_pl.html`` for Polish) before falling back to the
    original name.
    """

    def resolve_template(self, template):
        """Resolve the best-matching template for the request's language.

        If the language code is not ``"en"``, a language-specific variant is
        constructed by appending ``_<lang>.html`` before the ``.html``
        extension.  The language-specific variant is tried first; the
        original name serves as the fallback.

        Args:
            template (str | list[str] | tuple[str]): Template name(s).

        Returns:
            Template: The resolved Django template instance.
        """
        request = getattr(self, "_request", None)
        if request is not None and hasattr(request, "LANGUAGE_CODE"):
            lang = request.LANGUAGE_CODE[:2].lower()
        else:
            lang = "en"

        if lang == "en":
            return TemplateResponse.resolve_template(self, template)

        if isinstance(template, (list, tuple)):
            templates = []
            for pos in template:
                templates.append(pos.replace(".html", "_" + lang + ".html"))
                templates.append(pos)
            return loader.select_template(templates)

        if isinstance(template, str):
            return TemplateResponse.resolve_template(
                self,
                [template.replace(".html", "_" + lang + ".html"), template],
            )

        # Non-string, non-list -- return as-is (edge case).
        return template


class ExtTemplateResponse(LocalizationTemplateResponse):
    """A TemplateResponse subclass that renders templates as various document types.

    Supported output formats include HTML, PDF, SPDF (small-page PDF),
    OpenDocument (ODS/ODT/ODP), Office Open XML (XLSX/DOCX/PPTX),
    HTML-based documents (hdoc/hxls), TXT, and JSON.

    The constructor inspects the view's ``doc_type()`` return value and
    builds an appropriate list of template names (including doc-type-specific
    suffixes and system fallback templates).
    """

    def __init__(
        self,
        request,
        template,
        context=None,
        content_type=None,
        status=None,
        mimetype=None,
        current_app=None,
        charset=None,
        using=None,
    ):
        """Initialize the response with a doc-type-aware template list.

        Args:
            request (HttpRequest): The current request.
            template (str | list[str] | tuple[str]): Base template name(s).
            context (dict | None): Template context.  Must contain a ``"view"``
                key for doc-type resolution.
            content_type (str | None): HTTP Content-Type value.
            status (int | None): HTTP status code.
            mimetype (str | None): Deprecated; use *content_type*.
            current_app (str | None): Current Django application label.
            charset (str | None): Character set for the response.
            using (str | None): Database alias.
        """
        if context is None:
            context = {}
        context["template"] = template

        # Try to get a model-specific template first.
        template2 = None
        if context.get("view"):
            template2 = self._get_model_template(context, context["view"].doc_type())
            if template2 and len(template2) == 1 and template2[0] in template:
                template2 = None

        # If no model template found, build one based on doc_type.
        if template2 is None:
            template2 = self._build_template_list(context, template)

        # Log the resolved template(s).
        if hasattr(template2, "template"):
            LOGGER.info("template: %s", template2.template.name)
        else:
            LOGGER.info("templates: %s", template2)

        TemplateResponse.__init__(
            self,
            request,
            template2,
            context,
            content_type,
            status,
            current_app,
        )

    # ------------------------------------------------------------------
    # Template-name construction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_template_list(context, template):
        """Build an ordered list of template names for the requested doc type.

        The list is constructed as follows:

        1. If the context contains ``"template_name"``, it is appended with
           ``.html`` and placed at the front.
        2. Each name in *template* is transformed by replacing ``.html`` with
           the doc-type-specific suffix (e.g. ``_pdf.html``).
        3. If the doc type has a system fallback (e.g.
           ``schsys/table_pdf.html``), it is appended last.

        Args:
            context (dict): The template context.
            template (str | list[str] | tuple[str]): Original template name(s).

        Returns:
            list[str] | str: The constructed template name list, or the
            original *template* if no transformation applies.
        """
        view = context.get("view")
        if view is None:
            return template

        doc_type = view.doc_type()

        # -- PDF / SPDF / TXT / HDOC / HXLS (suffix-based) -----------------
        if doc_type in _DOC_TYPE_CONFIG:
            suffix, fallback = _DOC_TYPE_CONFIG[doc_type]
            return _make_suffix_template_list(context, template, suffix, fallback)

        # -- OpenDocument (ODS / ODT / ODP) --------------------------------
        if doc_type in _ODF_TYPES:
            return _make_extension_template_list(
                context, template, doc_type, "schsys/table." + doc_type
            )

        # -- Office Open XML (XLSX / DOCX / PPTX) -------------------------
        if doc_type in _OOXML_TYPES:
            return _make_extension_template_list(
                context, template, doc_type, "schsys/table." + doc_type
            )

        # -- HTML or unknown -- return the original template unchanged -----
        return template

    def _get_model_template(self, context, doc_type):
        """Attempt to obtain a template name from the model instance.

        Inspects the context for ``"object"`` or ``"object_list"`` keys and,
        if the corresponding model defines ``template_for_object`` or
        ``template_for_list``, delegates to that method.

        Args:
            context (dict): The template context.
            doc_type (str): The document type (e.g. ``"pdf"``).

        Returns:
            list[str] | None: A list of template names, or ``None``.
        """
        if not context:
            return None

        # Single-object template.
        if "object" in context:
            obj = context["object"] or getattr(self, "object", None)
            if obj is not None and hasattr(obj, "template_for_object"):
                view = context.get("view")
                t = obj.template_for_object(view, context, doc_type)
                if t:
                    return t

        # Object-list template.
        elif "view" in context and "object_list" in context:
            ol = context["object_list"]
            if hasattr(ol, "model") and hasattr(ol.model, "template_for_list"):
                view = context["view"]
                t = ol.model.template_for_list(view, ol.model, context, doc_type)
                if t:
                    return t

        return None

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def render(self):
        """Render the response content according to the view's doc type.

        * ODF types (ods/odt/odp) are rendered via :func:`render_odf`.
        * OOXML types (xlsx/docx/pptx) are rendered via :func:`render_ooxml`.
        * HTML-based types (hdoc/hxls) use ``HtmlViewerParser`` and
          produce OOXML output.
        * PDF / SPDF types first render as HTML and then convert via
          :func:`stream_from_html`.
        * JSON type parses the HTML output into a JSON structure using
          ``SimpleTabParserBase``.
        * All other types fall back to the parent ``TemplateResponse.render``.

        Returns:
            self: The response instance with ``content`` populated.
        """
        doc_type = self.context_data["view"].doc_type()

        # -- ODF (OpenDocument) --------------------------------------------
        if doc_type in _ODF_TYPES:
            return self._render_odf()

        # -- OOXML (Office Open XML) ---------------------------------------
        if doc_type in _OOXML_TYPES:
            return self._render_ooxml()

        # -- HDOC / HXLS (HTML-based documents) ----------------------------
        if doc_type in _HDOC_TYPES:
            return self._render_hdoc(doc_type)

        # -- HTML first, then optionally convert to PDF / SPDF / JSON ----
        ret = TemplateResponse.render(self)

        if doc_type == "pdf":
            self._convert_to_pdf("pdf")
        elif doc_type == "spdf":
            self._convert_to_pdf("spdf")
        elif doc_type == "json":
            self._convert_to_json()

        return ret

    # -- Private render helpers --------------------------------------------

    def _render_odf(self):
        """Render the template as an OpenDocument (ODS/ODT/ODP) file."""
        self["Content-Type"] = "application/vnd.oasis.opendocument.spreadsheet"
        context = self.resolve_context(self.context_data)
        file_out, file_in = render_odf(self.template_name, Context(context))
        if file_out:
            try:
                with open(file_out, "rb") as f:
                    self.content = f.read()
            finally:
                try:
                    os.remove(file_out)
                except OSError:
                    LOGGER.warning("Failed to remove temporary file: %s", file_out)
            file_in_name = os.path.basename(file_in)
            self["Content-Disposition"] = "attachment; filename=%s" % file_in_name
        return self

    def _render_ooxml(self):
        """Render the template as an Office Open XML (XLSX/DOCX/PPTX) file."""
        self["Content-Type"] = (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        context = self.resolve_context(self.context_data)
        stream_out = render_ooxml(self.template_name, Context(context))
        if isinstance(stream_out, tuple):
            with open(stream_out[0], "rb") as f:
                self.content = f.read()
            file_in_name = os.path.basename(stream_out[1])
        else:
            self.content = stream_out.getvalue()
            file_in_name = os.path.basename(self.template_name[0])
        self["Content-Disposition"] = "attachment; filename=%s" % file_in_name
        return self

    def _render_hdoc(self, doc_type):
        """Render the template as an HTML-based OOXML document (hdoc/hxls)."""
        context = self.resolve_context(self.context_data)
        t = loader.select_template(self.template_name)
        content = "" + t.render(context)

        if doc_type == "hdoc":
            self["Content-Type"] = (
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document"
            )
            from pytigon_lib.schhtml.docxdc import DocxDc as Dc

            file_name = os.path.basename(self.template_name[0]).replace("html", "docx")
        else:
            self["Content-Type"] = (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            from pytigon_lib.schhtml.xlsxdc import XlsxDc as Dc

            file_name = os.path.basename(self.template_name[0]).replace("html", "xlsx")

        from pytigon_lib.schhtml.htmlviewer import HtmlViewerParser

        output = io.BytesIO()
        dc = Dc(output_name=file_name, output_stream=output)
        dc.set_paging(False)
        p = HtmlViewerParser(dc=dc)
        p.feed(content)
        p.close()
        dc.end_page()

        self.content = output.getvalue()
        self["Content-Disposition"] = "attachment; filename=%s" % file_name
        return self

    def _convert_to_pdf(self, stream_type):
        """Convert the already-rendered HTML content to PDF (or SPDF).

        Args:
            stream_type (str): Either ``"pdf"`` or ``"spdf"``.
        """
        mime = "application/pdf" if stream_type == "pdf" else "application/spdf"
        ext = ".pdf" if stream_type == "pdf" else ".spdf"
        self["Content-Type"] = mime

        if isinstance(self.template_name, str):
            tname = self.template_name
        else:
            tname = self.template_name[0]

        filename = tname.rsplit("/", 1)[-1].replace(".html", ext)
        self["Content-Disposition"] = "attachment; filename=%s" % filename

        pdf_stream = stream_from_html(
            self.content,
            stream_type=stream_type,
            base_url="file://",
            info={"template_name": self.template_name},
        )
        self.content = pdf_stream.getvalue()

    def _convert_to_json(self):
        """Convert the already-rendered HTML content to JSON."""
        self["Content-Type"] = "application/json"

        mp = SimpleTabParserBase()
        mp.feed(self.content.decode("utf-8"))
        mp.close()

        row_title = mp.tables[-1][0]
        tab = mp.tables[-1][1:]

        if ":" in row_title[0]:
            x = row_title[0].split(":")
            title = x[0]
            _per_page, c = x[1].split("/")
            row_title[0] = title
        else:
            c = len(tab) - 1

        for i in range(len(row_title)):
            row_title[i] = "%d" % (i + 1)
        row_title[0] = "cid"
        row_title[-1] = "caction"
        row_title.append("id")

        tab2 = []
        for row in tab:
            d = dict(zip(row_title, row))
            if hasattr(row, "row_id"):
                d["id"] = row.row_id
            if hasattr(row, "class_attr"):
                d["class"] = row.class_attr
            tab2.append(d)

        result = {"total": c, "rows": tab2}
        self.content = schjson.json_dumps(result)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def rendered_content(self):
        """Return the freshly rendered content for the template and context.

        This property does **not** set the final content of the response.
        Call :meth:`render` or assign to ``content`` explicitly to set
        the response body.

        The rendering is attempted first with a plain ``Context``.  If that
        raises an exception, a ``RequestContext`` (which adds request-specific
        context processors) is tried as a fallback.

        Returns:
            str: The rendered template content.
        """
        template = self.resolve_template(self.template_name)
        context = self.resolve_context(self.context_data)

        # Try with the plain Context first (no request processors).
        try:
            return template.render(context, self._request)
        except Exception:
            LOGGER.debug(
                "rendered_content: Context render failed, trying RequestContext.",
                exc_info=True,
            )

        # Fall back to RequestContext (adds context processors).
        return template.render(RequestContext(self._request, context), self._request)


# ------------------------------------------------------------------
# Standalone helper functions for template-name construction
# ------------------------------------------------------------------


def _make_suffix_template_list(context, template, suffix, fallback=None):
    """Build a template list with doc-type-specific HTML suffixes.

    Example: for suffix ``"_pdf.html"`` and template ``"table.html"``,
    produces ``["table_pdf.html", "table.html"]``.

    Args:
        context (dict): The template context.
        template (str | list[str] | tuple[str]): Base template name(s).
        suffix (str): Suffix to insert before ``.html``.
        fallback (str | None): Optional system fallback template name.

    Returns:
        list[str]: Ordered template name list.
    """
    template2 = []
    if "template_name" in context:
        template2.append(context["template_name"] + ".html")
    for pos in template if isinstance(template, (list, tuple)) else [template]:
        if suffix in pos:
            template2.append(pos)
        else:
            template2.append(pos.replace(".html", suffix))
    if fallback is not None:
        template2.append(fallback)
    return template2


def _make_extension_template_list(context, template, doc_type, fallback=None):
    """Build a template list with a different file extension.

    Example: for *doc_type* ``"ods"`` and template ``"table.html"``,
    produces ``["table.ods"]``.

    Args:
        context (dict): The template context.
        template (str | list[str] | tuple[str]): Base template name(s).
        doc_type (str): New extension (without leading dot).
        fallback (str | None): Optional system fallback template name.

    Returns:
        list[str]: Ordered template name list.
    """
    template2 = []
    if "template_name" in context:
        template2.append(context["template_name"] + "." + doc_type)
    for pos in template if isinstance(template, (list, tuple)) else [template]:
        template2.append(pos.replace(".html", "." + doc_type))
    if fallback is not None:
        template2.append(fallback)
    return template2


class ExtTemplateView(generic.TemplateView):
    """A class-based view that supports multiple output document types.

    Uses :class:`ExtTemplateResponse` as the response class.  POST requests
    are handled identically to GET requests (delegated to ``get()``).

    The document type is determined by :meth:`doc_type`.
    """

    response_class = ExtTemplateResponse

    def post(self, request, *args, **kwargs):
        """Handle POST requests by delegating to ``get()``.

        Returns:
            HttpResponse: The rendered response.
        """
        return self.get(request, *args, **kwargs)

    def doc_type(self):
        """Determine the document type for the current request.

        Resolution order:

        1. If the URL ``target`` parameter starts with one of the known
           ``DOC_TYPES`` (e.g. ``"pdf"``), that type is returned.
        2. If the GET parameter ``json`` equals ``"1"``, ``"json"`` is
           returned.
        3. Otherwise defaults to ``"html"``.

        Returns:
            str: The document type identifier.
        """
        target = self.kwargs.get("target", "")
        for doc_type in DOC_TYPES:
            if target.startswith(doc_type):
                return doc_type
        if self.request.GET.get("json") == "1":
            return "json"
        return "html"


def render_to_response(
    template_name,
    context=None,
    content_type=None,
    status=None,
    using=None,
    request=None,
):
    """Render a template with the given context and return an HttpResponse.

    This is a convenience wrapper around
    :func:`django.template.loader.render_to_string`.

    Args:
        template_name (str | list[str]): Template name(s) to render.
        context (dict | None): Context dictionary.
        content_type (str | None): MIME type for the response.
        status (int | None): HTTP status code (default ``200``).
        using (str | None): Template engine name.
        request (HttpRequest | None): Request for context processors.

    Returns:
        HttpResponse: The rendered response.
    """
    content = loader.render_to_string(template_name, context, request, using=using)
    return HttpResponse(content, content_type, status)


def render_to_response_ext(request, template_name, context, doc_type="html"):
    """Render a template via :class:`ExtTemplateView` with a given doc type.

    The *context* dictionary is **not** mutated; a shallow copy is made
    to avoid side effects on the caller's dictionary.

    Args:
        request (HttpRequest): The current request.
        template_name (str): Template name to render.
        context (dict): Context data for the template.
        doc_type (str): Document type identifier (default ``"html"``).

    Returns:
        HttpResponse: The rendered response.
    """
    # Work on a copy to avoid mutating the caller's context dict.
    ctx = dict(context)
    ctx["target"] = doc_type
    ctx.pop("request", None)
    return ExtTemplateView.as_view(template_name=template_name)(request, **ctx)


# ------------------------------------------------------------------
# Decorators -- render function return value as various document types
# ------------------------------------------------------------------


def dict_to_template(template_name):
    """Decorator: render the returned dict as a template (HTML by default).

    The decorated function must return a dictionary (or an ``HttpResponse``,
    which is passed through unchanged).

    Special keys in the returned dictionary:

    * ``"redirect"`` -- an ``HttpResponseRedirect`` is returned.
    * ``"template_name"`` -- overrides the decorator's *template_name*.
    * ``"doc_type"`` -- sets the document type.

    Args:
        template_name (str): Default template name.

    Returns:
        callable: The decorator function.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            v = func(request, *args, **kwargs)
            if isinstance(v, HttpResponse):
                return v

            redirect = v.get("redirect")
            if redirect is not None:
                return HttpResponseRedirect(make_href(redirect))

            tpl = v.get("template_name", template_name)
            dt = v.get("doc_type", "html")

            if "template_name" in v:
                return render_to_response_ext(request, tpl, v, doc_type=dt)
            elif dt != "html":
                tpl = template_name.replace(".html", "." + dt)
            return render_to_response_ext(request, tpl, v, doc_type=dt)

        return wrapper

    return decorator


def dict_to_odf(template_name):
    """Decorator: render the returned dict as an OpenDocument template.

    The template name's ``.ods`` extension is replaced with the actual
    doc type when present in the returned dictionary.

    Args:
        template_name (str): Default template name (should end with
            ``.ods``).

    Returns:
        callable: The decorator function.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            v = func(request, *args, **kwargs)
            ctx = RequestContext(request, v)
            ext = v.get("doc_type", "ods")
            return render_to_response_ext(
                request,
                template_name.replace(".ods", "." + ext),
                ctx.flatten(),
                doc_type=ext,
            )

        return wrapper

    return decorator


def dict_to_ooxml(template_name):
    """Decorator: render the returned dict as an Office Open XML template.

    The template name's ``.xlsx`` extension is replaced with the actual
    doc type when present in the returned dictionary.

    Args:
        template_name (str): Default template name (should end with
            ``.xlsx``).

    Returns:
        callable: The decorator function.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            v = func(request, *args, **kwargs)
            ctx = RequestContext(request, v)
            ext = v.get("doc_type", "xlsx")
            return render_to_response_ext(
                request,
                template_name.replace(".xlsx", "." + ext),
                ctx.flatten(),
                doc_type=ext,
            )

        return wrapper

    return decorator


def dict_to_txt(template_name):
    """Decorator: render the returned dict as a plain-text template.

    Args:
        template_name (str): Template name.

    Returns:
        callable: The decorator function.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            v = func(request, *args, **kwargs)
            ctx = RequestContext(request, v)
            return render_to_response_ext(
                request, template_name, ctx.flatten(), doc_type="txt"
            )

        return wrapper

    return decorator


def dict_to_hdoc(template_name):
    """Decorator: render the returned dict as an HTML-based Word document.

    Args:
        template_name (str): Template name.

    Returns:
        callable: The decorator function.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            v = func(request, *args, **kwargs)
            ctx = RequestContext(request, v)
            return render_to_response_ext(
                request, template_name, ctx.flatten(), doc_type="hdoc"
            )

        return wrapper

    return decorator


def dict_to_hxls(template_name):
    """Decorator: render the returned dict as an HTML-based Excel document.

    Args:
        template_name (str): Template name.

    Returns:
        callable: The decorator function.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            v = func(request, *args, **kwargs)
            ctx = RequestContext(request, v)
            return render_to_response_ext(
                request, template_name, ctx.flatten(), doc_type="hxls"
            )

        return wrapper

    return decorator


def dict_to_pdf(template_name):
    """Decorator: render the returned dict as a PDF document.

    Args:
        template_name (str): Template name.

    Returns:
        callable: The decorator function.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            v = func(request, *args, **kwargs)
            ctx = RequestContext(request, v)
            return render_to_response_ext(
                request, template_name, ctx.flatten(), doc_type="pdf"
            )

        return wrapper

    return decorator


def dict_to_spdf(template_name):
    """Decorator: render the returned dict as a Small-Page PDF document.

    Args:
        template_name (str): Template name.

    Returns:
        callable: The decorator function.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(request, *args, **kwargs):
            v = func(request, *args, **kwargs)
            ctx = RequestContext(request, v)
            return render_to_response_ext(
                request, template_name, ctx.flatten(), doc_type="spdf"
            )

        return wrapper

    return decorator


def dict_to_json(func):
    """Decorator: render the returned dict/list as a JSON response.

    The decorated function must return a JSON-serializable object (usually
    a ``dict`` or ``list``).

    Args:
        func (callable): The view function.

    Returns:
        callable: The wrapped function.
    """

    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        v = func(request, *args, **kwargs)
        return HttpResponse(schjson.json_dumps(v), content_type="application/json")

    return wrapper


def dict_to_xml(func):
    """Decorator: render the returned data as an XML response.

    If the decorated function returns a ``str`` it is used directly.
    Otherwise the value is serialized with Django's XML serializer.

    Args:
        func (callable): The view function.

    Returns:
        callable: The wrapped function.
    """

    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        v = func(request, *args, **kwargs)
        if isinstance(v, str):
            return HttpResponse(v, content_type="application/xhtml+xml")
        return HttpResponse(
            serializers.serialize("xml", v),
            content_type="application/xhtml+xml",
        )

    return wrapper
