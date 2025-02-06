from django.template import loader, Context
from pytigon_lib.schdjangoext.spreadsheet_render import render_odf, render_ooxml
from pytigon_lib.schhtml.htmlviewer import stream_from_html
import os


def get_template_names(context, doc_type):
    """Generate template names based on context and document type."""
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
            if doc_type in ("html", "txt", "pdf", "hdoc")
            else f"{pos}.{doc_type}"
        )
        for pos in templates
    ]


def render_doc(context):
    """Render a document based on the provided context."""
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
                ret_attr["Content-Disposition"] = (
                    f"attachment; filename={os.path.basename(file_in)}"
                )
                ret_attr["Content-Type"] = (
                    "application/vnd.oasis.opendocument.spreadsheet"
                )

        elif doc_type in ("xlsx", "docx", "pptx"):
            file_out, file_in = render_ooxml(templates, Context(context))
            if file_out:
                with open(file_out, "rb") as f:
                    ret_content = f.read()
                os.remove(file_out)
                ret_attr["Content-Disposition"] = (
                    f"attachment; filename={os.path.basename(templates[0])}"
                )
                ret_attr["Content-Type"] = (
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        elif doc_type == "pdf":
            t = loader.select_template(templates)
            content = t.render(context)
            ret_attr["Content-Disposition"] = (
                f"attachment; filename={os.path.basename(templates[0]).replace('.html', '').replace('_pdf', '.pdf')}"
            )
            ret_attr["Content-Type"] = "application/pdf"
            pdf_stream = stream_from_html(
                content, stream_type="pdf", base_url="file://"
            )
            ret_content = pdf_stream.getvalue()

        elif doc_type == "spdf":
            t = loader.select_template(templates)
            content = t.render(context)
            ret_attr["Content-Disposition"] = (
                f"attachment; filename={os.path.basename(templates[0]).replace('.html', '').replace('_pdf', '.spdf')}"
            )
            ret_attr["Content-Type"] = "application/spdf"
            pdf_stream = stream_from_html(
                content, stream_type="spdf", base_url="file://"
            )
            ret_content = pdf_stream.getvalue()

        elif doc_type == "txt":
            ret_attr["Content-Disposition"] = (
                f"attachment; filename={os.path.basename(templates[0]).replace('.html', '').replace('_txt', '.txt')}"
            )
            ret_attr["Content-Type"] = "text/plain"
            t = loader.select_template(templates)
            ret_content = t.render(context)

        elif doc_type == "hdoc":
            t = loader.select_template(templates)
            content = t.render(context)
            ret_attr["Content-Disposition"] = (
                f"attachment; filename={os.path.basename(templates[0]).replace('.html', '').replace('_hdoc', '.docx')}"
            )
            ret_attr["Content-Type"] = (
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            from htmldocx import HtmlToDocx

            docx_parser = HtmlToDocx()
            ret_content = docx_parser.parse_html_string(content)

        else:
            ret_attr["Content-Disposition"] = (
                f"attachment; filename={os.path.basename(templates[0]).replace('_html', '')}"
            )
            ret_attr["Content-Type"] = "text/html"
            t = loader.select_template(templates)
            ret_content = t.render(context)

    except Exception as e:
        raise RuntimeError(f"Error rendering document: {e}")

    return ret_attr, ret_content
