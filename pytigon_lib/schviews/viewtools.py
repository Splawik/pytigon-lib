"""This module provides various utility functions and classes for handling template rendering,
response generation, and object manipulation in a Django web application.

Classes:
    LocalizationTemplateResponse: A TemplateResponse subclass that resolves templates based on the request's language code.
    ExtTemplateResponse: A LocalizationTemplateResponse subclass that handles rendering of various document types.
    ExtTemplateView: A generic.TemplateView subclass that uses ExtTemplateResponse for rendering.

Functions:
    transform_template_name(obj, request, template_name): Transforms the template name using an object's method if available.
    change_pos(request, app, tab, pk, forward=True, field=None, callback_fun=None): Changes the position of an object in a table.
    duplicate_row(request, app, tab, pk, field=None): Duplicates a given row in a database table.
    render_to_response(template_name, context=None, content_type=None, status=None, using=None, request=None): Renders a template with a given context and returns an HttpResponse.
    render_to_response_ext(request, template_name, context, doc_type="html"): Renders a template with a given context and document type, and returns an HttpResponse.
    dict_to_template(template_name): A decorator that renders the returned dictionary from a function as a template.
    dict_to_odf(template_name): A decorator that renders the returned dictionary from a function as an ODS template.
    dict_to_ooxml(template_name): A decorator that renders the returned dictionary from a function as an OOXML template.
    dict_to_txt(template_name): A decorator that renders the returned dictionary from a function as a plain text template.
    dict_to_hdoc(template_name): A decorator that renders the returned dictionary from a function as an HTML document (hdoc).
    dict_to_hxls(template_name): A decorator that renders the returned dictionary from a function as an HTML Excel document (hxls).
    dict_to_pdf(template_name): A decorator that renders the returned dictionary from a function as a PDF document.
    dict_to_spdf(template_name): A decorator that renders the returned dictionary from a function as a Small Page PDF document.
    dict_to_json(func): A decorator that transforms the returned dictionary from a function into a JSON response.
    dict_to_xml(func): A decorator that transforms the returned dictionary from a function into an XML response.
"""

import os
import os.path
import io
import logging

from django.apps import apps
from django.db.models import Max, Min
from django.http import HttpResponse, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.template import loader, RequestContext, Context
from django.views import generic
from django.core import serializers

from pytigon_lib.schdjangoext.tools import make_href
from pytigon_lib.schhtml.htmlviewer import stream_from_html
from pytigon_lib.schdjangoext.spreadsheet_render import render_odf, render_ooxml
from pytigon_lib.schtools import schjson
from pytigon_lib.schparser.html_parsers import SimpleTabParserBase

LOGGER = logging.getLogger(__name__)

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


def transform_template_name(obj, request, template_name):
    """
    This function allows to transform template name by obj method.
    If obj has method transform_template_name, this method is called.
    Otherwise template_name is returned unchanged.
    """
    if hasattr(obj, "transform_template_name"):
        return obj.transform_template_name(request, template_name)
    else:
        return template_name


def change_pos(request, app, tab, pk, forward=True, field=None, callback_fun=None):
    """
    Change position of object in table.

    Parameters:
        request (HttpRequest): django http request
        app (str): name of django app
        tab (str): name of table
        pk (int): id of object
        forward (bool, optional): if True, move forward, if False move backward. Defaults to True.
        field (str, optional): if not None, move in subset of objects which have this field equal to value of field in object with id=pk. Defaults to None.
        callback_fun (function, optional): if not None, this function is called with two arguments: obj and obj2, where obj is object with id=pk and obj2 is object to which obj is moved. Defaults to None.

    Returns:
        HttpResponse: response with target refresh_page if object has been moved, and NO if not.
    """
    model = apps.get_model(app, tab)
    obj = model.objects.get(id=pk)
    if field:
        query = model.objects.extra(
            where=[field + "_id=%s"], params=[getattr(obj, field).pk]
        )
    else:
        query = model.objects
    if forward:
        agr = query.filter(id__gt=int(pk)).aggregate(Min("id"))
        if "id__min" in agr:
            object_id_2 = agr["id__min"]
        else:
            return HttpResponse("NO")
    else:
        agr = query.filter(id__lt=int(pk)).aggregate(Max("id"))
        if "id__max" in agr:
            object_id_2 = agr["id__max"]
        else:
            return HttpResponse("NO")
    if object_id_2 == None:
        return HttpResponse("NO")
    obj2 = model.objects.get(id=object_id_2)
    tmp_id = obj.id
    obj.id = obj2.id
    obj2.id = tmp_id
    if callback_fun:
        callback_fun(obj, obj2)
    obj.save()
    obj2.save()
    return HttpResponse(
        """<head><meta name="TARGET" content="refresh_page" /></head><body>YES</body>"""
    )


def duplicate_row(request, app, tab, pk, field=None):
    """
    Duplicate given row in database table.

    Args:
        request: Django request object.
        app: Application name.
        tab: Table name.
        pk: Primary key of the row to be duplicated.
        field: Optional field name to filter records by.

    Returns:
        HttpResponse: response with YES if object has been duplicated, and NO if not.
    """
    model = apps.get_model(app, tab)
    obj = model.objects.get(id=pk)
    if obj:
        obj.id = None
        obj.save()
        return HttpResponse("YES")
    return HttpResponse("NO")


class LocalizationTemplateResponse(TemplateResponse):
    def resolve_template(self, template):
        """
        Resolves the appropriate template for the response based on the request's language code.

        If the language code is not "en", it attempts to find a language-specific version of
        the template by appending the language code (e.g., "_fr" for French) before the ".html"
        extension. If the template is a list or tuple, it constructs a list of templates with
        both the language-specific and original template names. If the template is a string,
        it creates a list with both the language-specific and original template names and
        calls the `resolve_template` method of the superclass to select a template.

        Args:
            template (Union[str, List[str], Tuple[str]]): The template name(s) to resolve.

        Returns:
            Template: The resolved template object.
        """

        lang = self._request.LANGUAGE_CODE[:2].lower()
        if lang != "en":
            if isinstance(template, (list, tuple)):
                templates = []
                for pos in template:
                    templates.append(pos.replace(".html", "_" + lang + ".html"))
                    templates.append(pos)
                return loader.select_template(templates)
            elif isinstance(template, str):
                return TemplateResponse.resolve_template(
                    self, [template.replace(".html", "_" + lang + ".html"), template]
                )
            else:
                return template
        else:
            return TemplateResponse.resolve_template(self, template)


class ExtTemplateResponse(LocalizationTemplateResponse):
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
        """
        Constructor for ExtTemplateResponse.

        Args:
            request (HttpRequest): The request object.
            template (Union[str, List[str], Tuple[str]]): The template name(s) to render.
            context (Dict[str, Any], optional): The context to use for template rendering.
            content_type (str, optional): The content type to return.
            status (int, optional): The HTTP status code to return.
            mimetype (str, optional): The MIME type to return.
            current_app (str, optional): The current app name.
            charset (str, optional): The charset to use for the response.
            using (str, optional): The database alias to use for the response.

        The constructor first calculates the template name(s) based on the request's language
        code and the doc type of the view. It then calls the constructor of the superclass with
        the calculated template name(s).
        """
        template2 = None
        context["template"] = template
        if context and "view" in context and context["view"]:
            template2 = self._get_model_template(context, context["view"].doc_type())
            if template2 and len(template2) == 1 and template2[0] in template:
                template2 = None
        if not template2:
            if context and "view" in context and context["view"].doc_type() == "pdf":
                template2 = []
                if "template_name" in context:
                    template2.append(context["template_name"] + ".html")
                for pos in template:
                    if "_pdf.html" in pos:
                        template2.append(pos)
                    else:
                        template2.append(pos.replace(".html", "_pdf.html"))
                template2.append("schsys/table_pdf.html")
            elif context and "view" in context and context["view"].doc_type() == "spdf":
                template2 = []
                if "template_name" in context:
                    template2.append(context["template_name"] + ".html")
                for pos in template:
                    if "_spdf.html" in pos:
                        template2.append(pos)
                    else:
                        template2.append(pos.replace(".html", "_spdf.html"))
                template2.append("schsys/table_spdf.html")
            elif context and "view" in context and context["view"].doc_type() == "txt":
                template2 = []
                if "template_name" in context:
                    template2.append(context["template_name"] + ".html")
                for pos in template:
                    if "_txt.html" in pos:
                        template2.append(pos)
                    else:
                        template2.append(pos.replace(".html", "_txt.html"))
            elif context and "view" in context and context["view"].doc_type() == "hdoc":
                template2 = []
                if "template_name" in context:
                    template2.append(context["template_name"] + ".html")
                for pos in template:
                    if "_hdoc.html" in pos:
                        template2.append(pos)
                    else:
                        template2.append(pos.replace(".html", "_hdoc.html"))
            elif context and "view" in context and context["view"].doc_type() == "hxls":
                template2 = []
                if "template_name" in context:
                    template2.append(context["template_name"] + ".html")
                for pos in template:
                    if "_hxls.html" in pos:
                        template2.append(pos)
                    else:
                        template2.append(pos.replace(".html", "_hxls.html"))
            elif (
                context
                and "view" in context
                and context["view"].doc_type() in ("ods", "odt", "odp")
            ):
                template2 = []
                if "template_name" in context:
                    template2.append(
                        context["template_name"] + "." + context["view"].doc_type()
                    )
                for pos in template:
                    template2.append(pos.replace(".html", ".ods"))
                template2.append("schsys/table.ods")
            elif (
                context
                and "view" in context
                and context["view"].doc_type() in ("xlsx", "docx", "pptx")
            ):
                template2 = []
                if "template_name" in context:
                    template2.append(
                        context["template_name"] + "." + context["view"].doc_type()
                    )
                for pos in template:
                    template2.append(
                        pos.replace(".html", "." + context["view"].doc_type())
                    )
                template2.append("schsys/table." + context["view"].doc_type())
            else:
                template2 = template

        if hasattr(template2, "template"):
            LOGGER.info("template: " + str(template2.template.name))
        else:
            LOGGER.info("templates: " + str(template2))
        TemplateResponse.__init__(
            self, request, template2, context, content_type, status, current_app
        )

    def _get_model_template(self, context, doc_type):
        """
        Try to get template from model based on context and doc_type

        If context has 'object' key, it calls template_for_object method
        on object instance. If context has 'object_list' key and 'view' key,
        it calls template_for_list method on object_list.model instance.

        Returns None if no template found.
        """
        if context and "object" in context:
            o = context["object"]
            v = context["view"]
            if not o:
                o = self.object
            if hasattr(o, "template_for_object"):
                t = o.template_for_object(v, context, doc_type)
                if t:
                    return t

        elif context and "view" in context and "object_list" in context:
            ol = context["object_list"]
            v = context["view"]
            if hasattr(ol, "model"):
                if hasattr(ol.model, "template_for_list"):
                    t = ol.model.template_for_list(v, ol.model, context, doc_type)
                    if t:
                        return t
        return None

    def render(self):
        """
        Try to render the response content.

        If the view's doc_type is not one of "html", "pdf", "spdf", "json", the
        response content will be rendered as a document of given type.

        If the view's doc_type is "pdf", the response content will be rendered
        as a PDF document using the 'stream_from_html' function.

        If the view's doc_type is "spdf", the response content will be rendered
        as a PDF document using the 'stream_from_html' function, but with
        'stream_type' set to 'spdf'.

        If the view's doc_type is "json", the response content will be rendered
        as a JSON string using the 'SimpleTabParserBase' class.

        :returns: The rendered response.
        """
        if self.context_data["view"].doc_type() in ("ods", "odt", "odp"):
            self["Content-Type"] = "application/vnd.oasis.opendocument.spreadsheet"
            file_out, file_in = render_odf(
                self.template_name, Context(self.resolve_context(self.context_data))
            )
            if file_out:
                f = open(file_out, "rb")
                self.content = f.read()
                f.close()
                os.remove(file_out)
                file_in_name = os.path.basename(file_in)
                self["Content-Disposition"] = "attachment; filename=%s" % file_in_name
            return self
        elif self.context_data["view"].doc_type() in ("xlsx", "docx", "pptx"):
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
        elif self.context_data["view"].doc_type() in ("hdoc", "hxls"):
            context = self.resolve_context(self.context_data)

            t = loader.select_template(self.template_name)
            content = "" + t.render(context)

            if self.context_data["view"].doc_type() == "hdoc":
                self["Content-Type"] = (
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                )

                from pytigon_lib.schhtml.docxdc import DocxDc as Dc

                file_name = os.path.basename(self.template_name[0]).replace(
                    "html", "docx"
                )
            else:
                self["Content-Type"] = (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

                from pytigon_lib.schhtml.xlsxdc import XlsxDc as Dc

                file_name = os.path.basename(self.template_name[0]).replace(
                    "html", "xlsx"
                )

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
        else:
            ret = TemplateResponse.render(self)
            if self.context_data["view"].doc_type() == "pdf":
                self["Content-Type"] = "application/pdf"
                if isinstance(self.template_name, str):
                    tname = self.template_name
                else:
                    tname = self.template_name[0]
                self["Content-Disposition"] = "attachment; filename=%s" % tname.split(
                    "/"
                )[-1].replace(".html", ".pdf")
                pdf_stream = stream_from_html(
                    self.content,
                    stream_type="pdf",
                    base_url="file://",
                    info={"template_name": self.template_name},
                )
                self.content = pdf_stream.getvalue()
            elif self.context_data["view"].doc_type() == "spdf":
                self["Content-Type"] = "application/spdf"
                if isinstance(self.template_name, str):
                    tname = self.template_name
                else:
                    tname = self.template_name[0]
                self["Content-Disposition"] = "attachment; filename=%s" % tname.split(
                    "/"
                )[-1].replace(".html", ".spdf")
                spdf_stream = stream_from_html(
                    self.content,
                    stream_type="spdf",
                    base_url="file://",
                    info={"template_name": self.template_name},
                )
                self.content = spdf_stream.getvalue()
            elif self.context_data["view"].doc_type() == "json":
                self["Content-Type"] = "application/json"

                mp = SimpleTabParserBase()
                mp.feed(self.content.decode("utf-8"))
                mp.close()

                row_title = mp.tables[-1][0]
                tab = mp.tables[-1][1:]

                if ":" in row_title[0]:
                    x = row_title[0].split(":")
                    title = x[0]
                    per_page, c = x[1].split("/")
                    row_title[0] = title
                else:
                    per_page = 1
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

                d = {}
                d["total"] = c
                d["rows"] = tab2

                self.content = schjson.json_dumps(d)

            return ret

    @property
    def rendered_content(self):
        """Returns the freshly rendered content for the template and context
        described by the TemplateResponse.

        This *does not* set the final content of the response. To set the
        response content, you must either call render(), or set the
        content explicitly using the value of this property.
        """
        template = self.resolve_template(self.template_name)
        context = self.resolve_context(self.context_data)
        try:
            content = template.render(context, self._request)
        except Exception:
            try:
                content = template.render(RequestContext(self._request, context))
            except Exception:
                content = template.render(context, self._request)
        return content


class ExtTemplateView(generic.TemplateView):
    response_class = ExtTemplateResponse

    def post(self, request, *args, **kwargs):
        """
        Handle POST requests: instantiate a generic class-based view and
        call its dispatch() method.
        """
        return self.get(request, *args, **kwargs)

    def doc_type(self):
        """
        Return the document type for this view.

        The document type is determined as follows.  If the target
        in the URL starts with one of the document types given in
        `DOC_TYPES`, then that document type is used.  If the
        "json" parameter is set to 1 in the GET arguments, then
        "json" is used.  Otherwise, "html" is used.

        Returns:
            str: The document type.
        """
        for doc_type in DOC_TYPES:
            if self.kwargs["target"].startswith(doc_type):
                return doc_type
        if "json" in self.request.GET and self.request.GET["json"] == "1":
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
    """
    Calls a template_name with a given context and returns an HttpResponse object with that rendered text.

    Required arguments:

        template_name: the name of the template to be rendered and returned.

    Optional arguments:

        context: A dictionary of values to add to the template context. By default, an
            empty dictionary will be used.

        content_type: The MIME type to use for the resulting document. Defaults to the value of
            the ``DEFAULT_CONTENT_TYPE`` setting.

        status: The status code for the response. Defaults to ``200``.

        using: The name of the template engine to use for loading the template.

        request: The request object used to generate this response. If not provided, the
            ``HttpRequest`` object will be used.

    Returns:
        An ``HttpResponse`` whose content is the result of the template rendering passed
        to this function. If ``content_type`` is specified, that MIME type is used.
        Otherwise the default ``DEFAULT_CONTENT_TYPE`` setting is used.
    """
    content = loader.render_to_string(template_name, context, request, using=using)
    return HttpResponse(content, content_type, status)


def render_to_response_ext(request, template_name, context, doc_type="html"):
    """
    Renders a template with a given context and returns an HttpResponse object.

    Args:
        request: The HTTP request object.
        template_name: The name of the template to be rendered.
        context: A dictionary containing context data to be passed to the template.
        doc_type: The document type to be set in the context, defaults to "html".

    Returns:
        An HttpResponse object with the rendered template content.
    """

    context["target"] = doc_type
    if "request" in context:
        del context["request"]
    return ExtTemplateView.as_view(template_name=template_name)(request, **context)


def dict_to_template(template_name):
    """
    A decorator that calls the decorated function with the given arguments and keyword arguments and renders the returned dictionary as a template.

    If the returned dictionary contains a key "redirect", a redirect is performed to the value of that key. If the returned dictionary contains a key "template_name", the template with that name is rendered with the returned dictionary as the context. If the returned dictionary contains a key "doc_type", the document type of the response is set to the value of that key. Otherwise, the document type is set to "html".

    :param template_name: The name of the template to be rendered.
    :return: A decorator that calls the decorated function with the given arguments and keyword arguments and renders the returned dictionary as a template.
    """

    def _dict_to_template(func):
        def inner(request, *args, **kwargs):
            v = func(request, *args, **kwargs)
            if isinstance(v, HttpResponse):
                return v
            elif "redirect" in v:
                return HttpResponseRedirect(make_href(v["redirect"]))
            elif "template_name" in v:
                if "doc_type" in v:
                    return render_to_response_ext(
                        request, v["template_name"], v, doc_type=v["doc_type"]
                    )
                else:
                    return render_to_response_ext(request, v["template_name"], v)
            else:
                if "doc_type" in v:
                    return render_to_response_ext(
                        request,
                        template_name.replace(".html", "." + v["doc_type"]),
                        v,
                        doc_type=v["doc_type"],
                    )
                else:
                    return render_to_response_ext(request, template_name, v)

        return inner

    return _dict_to_template


def dict_to_odf(template_name):
    """
    A decorator that calls the decorated function with the given arguments and keyword arguments and renders the returned dictionary as an OpenDocument Spreadsheet (ODS) template.

    If the returned dictionary contains a key "redirect", a redirect is performed to the value of that key. If the returned dictionary contains a key "template_name", the template with that name is rendered with the returned dictionary as the context. If the returned dictionary contains a key "doc_type", the document type of the response is set to the value of that key. Otherwise, the document type is set to "ods".

    :param template_name: The name of the template to be rendered.
    :return: A decorator that calls the decorated function with the given arguments and keyword arguments and renders the returned dictionary as an ODS template.
    """

    def _dict_to_template(func):
        def inner(request, *args, **kwargs):
            v = func(request, *args, **kwargs)
            c = RequestContext(request, v)
            if "doc_type" in v:
                ext = v["doc_type"]
            else:
                ext = "ods"
            return render_to_response_ext(
                request,
                template_name.replace(".ods", "." + ext),
                c.flatten(),
                doc_type=ext,
            )

        return inner

    return _dict_to_template


def dict_to_ooxml(template_name):
    """
    A decorator that calls the decorated function with the given arguments and keyword arguments and renders the returned dictionary as a Microsoft Open Office XML (OOXML) Spreadsheet (XLSX) template.

    If the returned dictionary contains a key "redirect", a redirect is performed to the value of that key. If the returned dictionary contains a key "template_name", the template with that name is rendered with the returned dictionary as the context. If the returned dictionary contains a key "doc_type", the document type of the response is set to the value of that key. Otherwise, the document type is set to "xlsx".

    :param template_name: The name of the template to be rendered.
    :return: A decorator that calls the decorated function with the given arguments and keyword arguments and renders the returned dictionary as an OOXML template.
    """

    def _dict_to_template(func):
        def inner(request, *args, **kwargs):
            v = func(request, *args, **kwargs)
            c = RequestContext(request, v)
            if "doc_type" in v:
                ext = v["doc_type"]
            else:
                ext = "xlsx"
            return render_to_response_ext(
                request,
                template_name.replace(".xlsx", "." + ext),
                c.flatten(),
                doc_type=ext,
            )

        return inner

    return _dict_to_template


def dict_to_txt(template_name):
    """
    A decorator that calls the decorated function with the given arguments and keyword arguments and renders the returned dictionary as a plain text template.

    If the returned dictionary contains a key "redirect", a redirect is performed to the value of that key. If the returned dictionary contains a key "template_name", the template with that name is rendered with the returned dictionary as the context. If the returned dictionary contains a key "doc_type", the document type of the response is set to the value of that key. Otherwise, the document type is set to "txt".

    :param template_name: The name of the template to be rendered.
    :return: A decorator that calls the decorated function with the given arguments and keyword arguments and renders the returned dictionary as a plain text template.
    """

    def _dict_to_template(func):
        def inner(request, *args, **kwargs):
            v = func(request, *args, **kwargs)
            c = RequestContext(request, v)
            return render_to_response_ext(
                request, template_name, c.flatten(), doc_type="txt"
            )

        return inner

    return _dict_to_template


def dict_to_hdoc(template_name):
    """
    A decorator that transforms the returned dictionary from the decorated function into an HTML document (hdoc).

    If the returned dictionary contains a key "redirect", a redirect is performed to the value of that key.
    If it contains a key "template_name", the specified template is rendered with the dictionary as the context.
    The document type of the response is set to "hdoc".

    :param template_name: The name of the template to be used for rendering.
    :return: A decorator function that processes the response dictionary and renders it as an hdoc document.
    """

    def _dict_to_template(func):
        def inner(request, *args, **kwargs):
            v = func(request, *args, **kwargs)
            c = RequestContext(request, v)
            return render_to_response_ext(
                request, template_name, c.flatten(), doc_type="hdoc"
            )

        return inner

    return _dict_to_template


def dict_to_hxls(template_name):
    """
    A decorator that transforms the returned dictionary from the decorated function into an HTML Excel document (hxls).

    If the returned dictionary contains a key "redirect", a redirect is performed to the value of that key.
    If it contains a key "template_name", the specified template is rendered with the dictionary as the context.
    The document type of the response is set to "hxls".

    :param template_name: The name of the template to be used for rendering.
    :return: A decorator function that processes the response dictionary and renders it as an hxls document.
    """

    def _dict_to_template(func):
        def inner(request, *args, **kwargs):
            v = func(request, *args, **kwargs)
            c = RequestContext(request, v)
            return render_to_response_ext(
                request, template_name, c.flatten(), doc_type="hxls"
            )

        return inner

    return _dict_to_template


def dict_to_pdf(template_name):
    """
    A decorator that transforms the returned dictionary from the decorated function into a PDF document.

    If the returned dictionary contains a key "redirect", a redirect is performed to the value of that key.
    If it contains a key "template_name", the specified template is rendered with the dictionary as the context.
    The document type of the response is set to "pdf".

    :param template_name: The name of the template to be used for rendering.
    :return: A decorator function that processes the response dictionary and renders it as a PDF document.
    """

    def _dict_to_template(func):
        def inner(request, *args, **kwargs):
            v = func(request, *args, **kwargs)
            c = RequestContext(request, v)
            return render_to_response_ext(
                request, template_name, c.flatten(), doc_type="pdf"
            )

        return inner

    return _dict_to_template


def dict_to_spdf(template_name):
    """
    A decorator that transforms the returned dictionary from the decorated function into a PDF document using the Small Page PDF template.

    If the returned dictionary contains a key "redirect", a redirect is performed to the value of that key.
    If it contains a key "template_name", the specified template is rendered with the dictionary as the context.
    The document type of the response is set to "spdf".

    :param template_name: The name of the template to be used for rendering.
    :return: A decorator function that processes the response dictionary and renders it as a PDF document.
    """

    def _dict_to_template(func):
        def inner(request, *args, **kwargs):
            v = func(request, *args, **kwargs)
            c = RequestContext(request, v)
            return render_to_response_ext(
                request, template_name, c.flatten(), doc_type="spdf"
            )

        return inner

    return _dict_to_template


def dict_to_json(func):
    """
    A decorator that transforms the returned dictionary from the decorated function into a JSON response.

    The decorated function should return a dictionary that will be serialized into JSON format.
    The JSON response is returned with the content type set to "application/json".

    :param func: The function to be decorated.
    :return: A decorator function that processes the response dictionary and returns it as a JSON response.
    """

    def inner(request, *args, **kwargs):
        v = func(request, *args, **kwargs)
        return HttpResponse(schjson.json_dumps(v), content_type="application/json")

    return inner


def dict_to_xml(func):
    """
    A decorator that transforms the returned dictionary from the decorated function into an XML response.

    The decorated function should return a dictionary that will be serialized into XML format.
    The XML response is returned with the content type set to "application/xhtml+xml".

    :param func: The function to be decorated.
    :return: A decorator function that processes the response dictionary and returns it as an XML response.
    """

    def inner(request, *args, **kwargs):
        v = func(request, *args, **kwargs)
        if isinstance(v, str):
            return HttpResponse(v, content_type="application/xhtml+xml")
        else:
            return HttpResponse(
                serializers.serialize("xml", v), content_type="application/xhtml+xml"
            )

    return inner
