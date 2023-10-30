#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

# Pytigon - wxpython and django application framework

# author: "Slawomir Cholaj (slawomir.cholaj@gmail.com)"
# copyright: "Copyright (C) ????/2012 Slawomir Cholaj"
# license: "LGPL 3.0"
# version: "0.1a"

import os
import os.path
import io
import logging
from re import template

LOGGER = logging.getLogger(__name__)

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
    if hasattr(obj, "transform_template_name"):
        return obj.transform_template_name(request, template_name)
    else:
        return template_name


def change_pos(request, app, tab, pk, forward=True, field=None, callback_fun=None):
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
            HttpResponse("NO")
    else:
        agr = query.filter(id__lt=int(pk)).aggregate(Max("id"))
        if "id__max" in agr:
            object_id_2 = agr["id__max"]
        else:
            HttpResponse("NO")
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
    model = apps.get_model(app, tab)
    obj = model.objects.get(id=pk)
    if obj:
        obj.id = None
        obj.save()
        return HttpResponse("YES")
    return HttpResponse("NO")


class LocalizationTemplateResponse(TemplateResponse):
    def resolve_template(self, template):
        lang = self._request.LANGUAGE_CODE[:2].lower()
        if lang != "en":
            if isinstance(template, (list, tuple)):
                templates = []
                for pos in template:
                    templates.append(pos.replace(".html", "_" + lang + ".html"))
                    templates.append(pos)
                return loader.select_template(templates)
            elif type(template) == str:
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
            self[
                "Content-Type"
            ] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            context = self.resolve_context(self.context_data)
            stream_out = render_ooxml(self.template_name, Context(context))
            if type(stream_out) == tuple:
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
                self[
                    "Content-Type"
                ] = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

                from pytigon_lib.schhtml.docxdc import DocxDc as Dc

                file_name = os.path.basename(self.template_name[0]).replace(
                    "html", "docx"
                )
            else:
                self[
                    "Content-Type"
                ] = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

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
                if type(self.template_name) == str:
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
                if type(self.template_name) == str:
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
        except:
            try:
                content = template.render(RequestContext(self._request, context))
            except:
                content = template.render(context, self._request)
        return content


class ExtTemplateView(generic.TemplateView):
    response_class = ExtTemplateResponse

    def post(self, request, *args, **kwargs):
        return self.get(request, *args, **kwargs)

    def doc_type(self):
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
    content = loader.render_to_string(template_name, context, request, using=using)
    return HttpResponse(content, content_type, status)


def render_to_response_ext(request, template_name, context, doc_type="html"):
    context["target"] = doc_type
    if "request" in context:
        del context["request"]
    return ExtTemplateView.as_view(template_name=template_name)(request, **context)


def dict_to_template(template_name):
    def _dict_to_template(func):
        def inner(request, *args, **kwargs):
            v = func(request, *args, **kwargs)
            if isinstance(v, HttpResponse):
                return v
            elif "redirect" in v:
                return HttpResponseRedirect(make_href(v["redirect"]))
            elif "template_name" in v:
                # return render_to_response(v["template_name"], v, request=request)
                if "doc_type" in v:
                    return render_to_response_ext(
                        request, v["template_name"], v, doc_type=v["doc_type"]
                    )
                else:
                    return render_to_response_ext(request, v["template_name"], v)
            else:
                # return render_to_response(template_name, v, request=request)
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
    def _dict_to_template(func):
        def inner(request, *args, **kwargs):
            v = func(request, *args, **kwargs)
            c = RequestContext(request, v)
            return render_to_response_ext(
                request, template_name, c.flatten(), doc_type="pdf"
            )

        return inner

    return _dict_to_template


def dict_to_pdf(template_name):
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
    def inner(request, *args, **kwargs):
        v = func(request, *args, **kwargs)
        return HttpResponse(schjson.json_dumps(v), content_type="application/json")

    return inner


def dict_to_xml(func):
    def inner(request, *args, **kwargs):
        v = func(request, *args, **kwargs)
        if type(v) == "str":
            return HttpResponse(v, content_type="application/xhtml+xml")
        else:
            return HttpResponse(
                serializers.serialize("xml", v), content_type="application/xhtml+xml"
            )

    return inner
