"""
The module enables the dynamic creation of documents in a odf format (https://en.wikipedia.org/wiki/OpenDocument).
Process of documents creation begins with the creation of the template. It is also in odf format.
Template is a normal static document supplemented with dynamic structures placed in comments to the selected cells.
The syntax of these additional comments is consistent with django. There are additional syntax elements
to control the place where dynamic structures are activated.
"""

import os
import io
from zipfile import ZipFile
import xml.dom.minidom

from django.template import Template, Context
from django.http import HttpResponse
from django.conf import settings
from django.template.exceptions import TemplateDoesNotExist

from pytigon_lib.schfs.vfstools import get_temp_filename
from pytigon_lib.schspreadsheet.odf_process import OdfDocTransform
from pytigon_lib.schspreadsheet.ooxml_process import OOXmlDocTransform

template_dirs = getattr(settings, "TEMPLATES")[0]["DIRS"]


class OdfDocTemplateTransform(OdfDocTransform):
    def process_template(self, doc_str, context):
        """Process the template string with the given context."""
        return Template(
            "{% load exsyntax %}{% load exfiltry %}{% load expr %}{% load l10n %}{% localize off %}"
            + doc_str
            + "{% endlocalize %}"
        ).render(context)


class OOXmlDocTemplateTransform(OOXmlDocTransform):
    def process_template(self, doc_str, context):
        """Process the template string with the given context."""
        return Template(
            "{% load exsyntax %}{% load exfiltry %}{% load expr %}{% load l10n %}{% localize off %}"
            + doc_str
            + "{% endlocalize %}"
        ).render(context)


def oo_dict(template_name):
    """Extract table names from the ODF template."""
    file_name = None
    for template_dir in template_dirs:
        if os.path.exists(os.path.join(template_dir, template_name)):
            file_name = os.path.join(template_dir, template_name)

    if file_name:
        try:
            with ZipFile(file_name, "r") as z:
                doc_content = z.read("content.xml")
                if isinstance(doc_content, bytes):
                    doc_content = doc_content.decode("utf-8")
                doc = xml.dom.minidom.parseString(doc_content.replace("&apos;", "'"))
                elements = doc.getElementsByTagName("table:table")
                return [
                    (elem.getAttribute("table:name"), elem.getAttribute("table:name"))
                    for elem in elements
                ]
        except Exception as e:
            raise RuntimeError(f"Failed to process template: {e}")
    else:
        raise RuntimeError(f"Failed to find template: {template_name}")


class DefaultTbl:
    """Default table class for managing row and column positions."""

    def __init__(self):
        self.row = -1
        self.col = -1

    def inc_row(self, row=1):
        """Increment the row position."""
        self.row += row
        return ""

    def inc_col(self, col=1):
        """Increment the column position."""
        self.col += col
        return ""

    def set_col(self, col):
        """Set the column position."""
        self.col = col
        return ""

    def set_row(self, row):
        """Set the row position."""
        self.row = row
        return ""


def _render_doc(
    doc_type, template_name, context_instance=None, output_name=None, debug=None
):
    """Render the document and return the output file name and template name."""

    if context_instance is None:
        context_instance = {}

    if type(context_instance) is dict:
        context_instance = Context(context_instance)

    context = (
        {"tbl": DefaultTbl()} if "tbl" not in context_instance else context_instance
    )

    try:
        with context_instance.push(context):
            if "tbl" not in context_instance:
                context_instance["tbl"] = DefaultTbl()

            if isinstance(template_name, (list, tuple)):
                name = _find_template(template_name)
            else:
                name = _find_template((template_name,))

            if output_name:
                name_out = output_name
            else:
                name_out = get_temp_filename()
            doc_class = (
                OdfDocTemplateTransform
                if doc_type.lower().startswith("od")
                else OOXmlDocTemplateTransform
            )
            doc = doc_class(name, name_out)

            if doc.process(context_instance, debug) != 1:
                os.remove(name_out)
                return None, name

            return name_out, name
    except Exception as e:
        raise RuntimeError(f"Failed to render document: {e}")


def _find_template(template_names):
    """Find the first existing template from the list."""
    for tname in template_names:
        if tname.startswith("/") or ":" in tname:
            if os.path.exists(tname):
                return tname
        else:
            for template_dir in template_dirs:
                name = os.path.join(template_dir, tname)
                if os.path.exists(name):
                    return name
    raise TemplateDoesNotExist(";".join(template_names))


def _render_doc_to_response(
    doc_type, doc_content_type, template_name, context_instance=None, debug=None
):
    """Render the document and return it as an HttpResponse."""
    try:
        s = _render_doc(doc_type, template_name, context_instance, debug)
        if not s[0]:
            return None

        name = s[1].split("_")[1] if "_" in s[1] else s[1]
        response = HttpResponse()
        response["Content-Disposition"] = f"attachment; filename={name}"
        response["Content-Type"] = doc_content_type

        with open(s[0], "rb") as f:
            response.content = f.read()
        os.remove(s[0])
        return response
    except Exception as e:
        raise RuntimeError(f"Failed to render document to response: {e}")


def render_odf(template_name, context_instance=None, output_name=None, debug=None):
    """Render an ODF document."""
    return _render_doc("ODF", template_name, context_instance, output_name, debug)


def render_ooxml(template_name, context_instance=None, output_name=None, debug=None):
    """Render an OOXML document."""
    return _render_doc("OOXML", template_name, context_instance, output_name, debug)


def render_to_response_odf(template_name, context_instance=None, debug=None):
    """Render an ODF document and return it as an HttpResponse."""
    return _render_doc_to_response(
        "ODF",
        "application/vnd.oasis.opendocument.spreadsheet",
        template_name,
        context_instance,
        debug,
    )


def render_to_response_ooxml(template_name, context_instance=None, debug=None):
    """Render an OOXML document and return it as an HttpResponse."""
    return _render_doc_to_response(
        "OOXML",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        template_name,
        context_instance,
        debug,
    )
