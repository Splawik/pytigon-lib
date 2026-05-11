"""Document rendering utilities for various output formats.

Supports HTML, PDF, spdf, plain text, ODF, OOXML, and hdoc (HTML to
DOCX) document generation through template-based rendering.
"""

import os

from django.template import loader, Context
from pytigon_lib.schdjangoext.spreadsheet_render import render_odf, render_ooxml
from pytigon_lib.schhtml.htmlviewer import stream_from_html

# Mapping of document types to their MIME content types.
CONTENT_TYPE_MAP = {
    "ods": "application/vnd.oasis.opendocument.spreadsheet",
    "odt": "application/vnd.oasis.opendocument.text",
    "odp": "application/vnd.oasis.opendocument.presentation",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "pdf": "application/pdf",
    "spdf": "application/spdf",
    "txt": "text/plain",
    "hdoc": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "html": "text/html",
}


def get_template_names(context, doc_type):
    """Generate prioritized template names from context and document type.

    Templates listed in ``context["template_names"]`` are tried first,
    followed by a default ``schsys/object_list`` or ``schsys/object``
    template depending on whether ``object_list`` is present in context.

    Args:
        context: Template context dict.
        doc_type: Document type string (e.g. ``"html"``, ``"pdf"``).

    Returns:
        List of template name strings.
    """
    templates = []
    if "template_names" in context:
        t = context["template_names"]
        templates.extend(t if isinstance(t, (tuple, list)) else [t])

    templates.append(
        "schsys/object_list" if "object_list" in context else "schsys/object"
    )

    return [
        (
            f"{pos}_{doc_type}.html"
            if doc_type in ("html", "txt", "pdf", "hdoc", "spdf")
            else f"{pos}.{doc_type}"
        )
        for pos in templates
    ]


def _build_disposition(template_path, doc_type, file_in=None):
    """Build the Content-Disposition header value.

    Args:
        template_path: Path to the first matched template.
        doc_type: Document type string.
        file_in: Optional alternative filename (used by ODF/OOXML).

    Returns:
        Content-Disposition header string.
    """
    if file_in:
        return f"attachment; filename={os.path.basename(file_in)}"
    base = os.path.basename(template_path)
    base = base.replace(".html", "").replace(f"_{doc_type}", f".{doc_type}")
    return f"attachment; filename={base}"


def _render_pdf_like(context, templates, doc_type):
    """Render a PDF or spdf document from an HTML template.

    Args:
        context: Template context dict.
        templates: List of template names.
        doc_type: ``"pdf"`` or ``"spdf"``.

    Returns:
        Tuple of (attr_dict, content_bytes).
    """
    t = loader.select_template(templates)
    content = t.render(context)
    attr = {
        "Content-Disposition": _build_disposition(templates[0], doc_type),
        "Content-Type": CONTENT_TYPE_MAP.get(doc_type, "application/octet-stream"),
    }
    pdf_stream = stream_from_html(content, stream_type=doc_type, base_url="file://")
    return attr, pdf_stream.getvalue()


def render_doc(context):
    """Render a document in the format specified by ``context["doc_type"]``.

    Supported document types:

    - ``ods``, ``odt``, ``odp`` — OpenDocument formats.
    - ``xlsx``, ``docx``, ``pptx`` — Office Open XML formats.
    - ``pdf`` — PDF via WeasyPrint or similar.
    - ``spdf`` — Simplified/screen PDF.
    - ``txt`` — Plain text.
    - ``hdoc`` — HTML converted to DOCX via ``htmldocx``.
    - ``html`` — Raw HTML (default fallback).

    Args:
        context: Template context dict. Must contain at least
            ``"doc_type"``; optionally ``"template_names"`` and
            ``"object_list"``.

    Returns:
        Tuple of (attr_dict, content_bytes) where ``attr_dict``
        contains ``Content-Type`` and ``Content-Disposition`` keys.

    Raises:
        RuntimeError: If rendering fails for any reason.
    """
    ret_attr = {}
    ret_content = None
    doc_type = context.get("doc_type", "html")
    templates = get_template_names(context, doc_type)

    try:
        if doc_type in ("ods", "odt", "odp"):
            file_out, file_in = render_odf(templates, Context(context))
            if file_out:
                with open(file_out, "rb") as f:
                    ret_content = f.read()
                os.remove(file_out)
                ret_attr["Content-Disposition"] = _build_disposition(
                    templates[0], doc_type, file_in
                )
                ret_attr["Content-Type"] = CONTENT_TYPE_MAP.get(
                    doc_type, "application/octet-stream"
                )

        elif doc_type in ("xlsx", "docx", "pptx"):
            file_out, file_in = render_ooxml(templates, Context(context))
            if file_out:
                with open(file_out, "rb") as f:
                    ret_content = f.read()
                os.remove(file_out)
                ret_attr["Content-Disposition"] = _build_disposition(
                    templates[0], doc_type, file_in
                )
                ret_attr["Content-Type"] = CONTENT_TYPE_MAP.get(
                    doc_type, "application/octet-stream"
                )

        elif doc_type in ("pdf", "spdf"):
            ret_attr, ret_content = _render_pdf_like(context, templates, doc_type)

        elif doc_type == "txt":
            t = loader.select_template(templates)
            ret_content = t.render(context)
            ret_attr["Content-Disposition"] = _build_disposition(templates[0], doc_type)
            ret_attr["Content-Type"] = CONTENT_TYPE_MAP["txt"]

        elif doc_type == "hdoc":
            t = loader.select_template(templates)
            content = t.render(context)
            ret_attr["Content-Disposition"] = _build_disposition(templates[0], doc_type)
            ret_attr["Content-Type"] = CONTENT_TYPE_MAP["hdoc"]
            from htmldocx import HtmlToDocx

            docx_parser = HtmlToDocx()
            ret_content = docx_parser.parse_html_string(content)

        else:  # html (default)
            t = loader.select_template(templates)
            ret_content = t.render(context)
            ret_attr["Content-Disposition"] = _build_disposition(templates[0], "html")
            ret_attr["Content-Type"] = CONTENT_TYPE_MAP["html"]

    except Exception as e:
        raise RuntimeError(f"Error rendering document: {e}") from e

    return ret_attr, ret_content
