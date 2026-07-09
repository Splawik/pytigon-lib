from unittest.mock import MagicMock, patch

import pytest
from django.template import Context

from pytigon_lib.schdjangoext.render import (
    CONTENT_TYPE_MAP,
    _build_disposition,
    _render_pdf_like,
    get_template_names,
    render_doc,
)


class TestGetTemplateNames:
    def test_template_names_string(self):
        context = {"template_names": "myapp/custom"}
        names = get_template_names(context, "html")
        assert any("myapp/custom_html.html" in n for n in names)

    def test_template_names_tuple(self):
        context = {"template_names": ("t1", "t2")}
        names = get_template_names(context, "pdf")
        assert any("t1_pdf.html" in n for n in names)
        assert any("t2_pdf.html" in n for n in names)

    def test_no_template_names_with_object_list(self):
        context = {"object_list": [1, 2]}
        names = get_template_names(context, "html")
        assert all(n in ("schsys/object_list_html.html",) for n in names)

    def test_no_template_names_no_object_list(self):
        context = {}
        names = get_template_names(context, "html")
        assert all(n in ("schsys/object_html.html",) for n in names)

    def test_non_pdf_like_type_adds_extension(self):
        context = {"template_names": "myapp/report"}
        names = get_template_names(context, "ods")
        assert any("myapp/report.ods" in n for n in names)

    def test_docx_type_uses_docx_extension(self):
        context = {"template_names": "myapp/report"}
        names = get_template_names(context, "docx")
        assert any("myapp/report.docx" in n for n in names)

    def test_pptx_type_uses_pptx_extension(self):
        context = {"template_names": "myapp/report"}
        names = get_template_names(context, "pptx")
        assert any("myapp/report.pptx" in n for n in names)


class TestBuildDisposition:
    def test_build_with_file_in(self):
        result = _build_disposition("/templates/x.html", "pdf", file_in="/output/result.ods")
        assert "attachment; filename=result.ods" == result

    def test_build_no_file_in_basic(self):
        result = _build_disposition("/templates/myapp/test_pdf.html", "pdf")
        assert "filename=test.pdf" in result

    def test_build_no_html_in_name(self):
        result = _build_disposition("/templates/myapp/template_html.html", "html")
        assert "filename=template.html" in result


class TestRenderPdfLike:
    def test_render_pdf_like_returns_attr_and_content(self):
        context = {"key": "val"}
        templates = ["test_pdf.html"]

        mock_template = MagicMock()
        mock_template.render.return_value = "<html>pdf</html>"

        mock_stream = MagicMock()
        mock_stream.getvalue.return_value = b"pdf_bytes"

        with patch("pytigon_lib.schdjangoext.render.loader.select_template", return_value=mock_template):
            with patch("pytigon_lib.schdjangoext.render.stream_from_html", return_value=mock_stream):
                attr, content = _render_pdf_like(context, templates, "pdf")
                assert attr["Content-Type"] == "application/pdf"
                assert "Content-Disposition" in attr
                assert content == b"pdf_bytes"

    def test_render_spdf(self):
        context = {}
        templates = ["test_spdf.html"]
        mock_template = MagicMock()
        mock_template.render.return_value = "<html>spdf</html>"
        mock_stream = MagicMock()
        mock_stream.getvalue.return_value = b"spdf_bytes"

        with patch("pytigon_lib.schdjangoext.render.loader.select_template", return_value=mock_template):
            with patch("pytigon_lib.schdjangoext.render.stream_from_html", return_value=mock_stream):
                attr, content = _render_pdf_like(context, templates, "spdf")
                assert attr["Content-Type"] == "application/spdf"


class TestRenderDoc:
    def test_render_doc_html_default(self):
        context = {"doc_type": "html"}
        mock_template = MagicMock()
        mock_template.render.return_value = "<html><body>Hi</body></html>"

        with patch("pytigon_lib.schdjangoext.render.loader.select_template", return_value=mock_template):
            attr, content = render_doc(context)
            assert attr["Content-Type"] == "text/html"
            assert content == "<html><body>Hi</body></html>"

    def test_render_doc_txt(self):
        context = {"doc_type": "txt"}
        mock_template = MagicMock()
        mock_template.render.return_value = "plain text"

        with patch("pytigon_lib.schdjangoext.render.loader.select_template", return_value=mock_template):
            attr, content = render_doc(context)
            assert attr["Content-Type"] == "text/plain"

    def test_render_doc_default_doc_type(self):
        context = {}
        mock_template = MagicMock()
        mock_template.render.return_value = "<html></html>"

        with patch("pytigon_lib.schdjangoext.render.loader.select_template", return_value=mock_template):
            attr, content = render_doc(context)
            assert attr["Content-Type"] == "text/html"

    def test_render_doc_unknown_type_fallsback_to_html(self):
        context = {"doc_type": "unknown"}
        mock_template = MagicMock()
        mock_template.render.return_value = "<html></html>"

        with patch("pytigon_lib.schdjangoext.render.loader.select_template", return_value=mock_template):
            attr, content = render_doc(context)
            assert attr["Content-Type"] == "text/html"

    def test_render_doc_error_raises_runtime_error(self):
        context = {"doc_type": "html"}
        with patch("pytigon_lib.schdjangoext.render.loader.select_template", side_effect=RuntimeError("fail")):
            with pytest.raises(RuntimeError, match="Error rendering document"):
                render_doc(context)
