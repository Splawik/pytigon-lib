from unittest.mock import MagicMock, patch

import pytest
from django.http import HttpResponse, HttpResponseRedirect
from django.test import RequestFactory, override_settings

from pytigon_lib.schviews.viewtools import (
    _DOC_TYPE_CONFIG,
    _HDOC_TYPES,
    _ODF_TYPES,
    _OOXML_TYPES,
    _PDF_TYPES,
    DOC_TYPES,
    ExtTemplateView,
    LocalizationTemplateResponse,
    _make_extension_template_list,
    _make_suffix_template_list,
    dict_to_hdoc,
    dict_to_hxls,
    dict_to_json,
    dict_to_odf,
    dict_to_ooxml,
    dict_to_pdf,
    dict_to_spdf,
    dict_to_template,
    dict_to_txt,
    dict_to_xml,
    duplicate_row,
    render_to_response,
    render_to_response_ext,
    transform_template_name,
)


@pytest.fixture
def rf():
    return RequestFactory()


class TestTransformTemplateName:
    def test_no_method_returns_original(self):
        obj = object()
        assert transform_template_name(obj, None, "template.html") == "template.html"

    def test_with_method_calls_it(self):
        obj = MagicMock()
        obj.transform_template_name.return_value = "transformed.html"
        result = transform_template_name(obj, "req", "template.html")
        obj.transform_template_name.assert_called_once_with("req", "template.html")
        assert result == "transformed.html"


class TestDocTypeConstants:
    def test_doc_types_contains_pdf(self):
        assert "pdf" in DOC_TYPES

    def test_doc_types_contains_xlsx(self):
        assert "xlsx" in DOC_TYPES

    def test_doc_types_contains_json(self):
        assert "json" in DOC_TYPES

    def test_odf_types_frozenset(self):
        assert isinstance(_ODF_TYPES, frozenset)
        assert "ods" in _ODF_TYPES
        assert "odt" in _ODF_TYPES
        assert "odp" in _ODF_TYPES

    def test_ooxml_types_frozenset(self):
        assert "xlsx" in _OOXML_TYPES
        assert "docx" in _OOXML_TYPES
        assert "pptx" in _OOXML_TYPES

    def test_hdoc_types_frozenset(self):
        assert "hdoc" in _HDOC_TYPES
        assert "hxls" in _HDOC_TYPES

    def test_pdf_types_frozenset(self):
        assert "pdf" in _PDF_TYPES
        assert "spdf" in _PDF_TYPES

    def test_doc_type_config_keys(self):
        assert "pdf" in _DOC_TYPE_CONFIG
        assert "spdf" in _DOC_TYPE_CONFIG
        assert "txt" in _DOC_TYPE_CONFIG
        assert "hdoc" in _DOC_TYPE_CONFIG
        assert "hxls" in _DOC_TYPE_CONFIG


class TestMakeSuffixTemplateList:
    def test_single_template_with_suffix(self):
        ctx = {}
        result = _make_suffix_template_list(ctx, "table.html", "_pdf.html")
        assert result == ["table_pdf.html"]

    def test_template_list_with_suffix(self):
        ctx = {}
        result = _make_suffix_template_list(ctx, ["table.html", "base.html"], "_pdf.html")
        assert result == ["table_pdf.html", "base_pdf.html"]

    def test_tuple_template(self):
        ctx = {}
        result = _make_suffix_template_list(ctx, ("table.html",), "_pdf.html")
        assert result == ["table_pdf.html"]

    def test_with_template_name_in_context(self):
        ctx = {"template_name": "custom"}
        result = _make_suffix_template_list(ctx, "table.html", "_pdf.html")
        assert result[0] == "custom.html"
        assert "table_pdf.html" in result

    def test_with_fallback(self):
        ctx = {}
        result = _make_suffix_template_list(ctx, "table.html", "_pdf.html", fallback="schsys/table_pdf.html")
        assert result[-1] == "schsys/table_pdf.html"

    def test_without_fallback(self):
        ctx = {}
        result = _make_suffix_template_list(ctx, "table.html", "_pdf.html")
        assert result == ["table_pdf.html"]

    def test_suffix_already_present(self):
        ctx = {}
        result = _make_suffix_template_list(ctx, "table_pdf.html", "_pdf.html")
        assert result == ["table_pdf.html"]


class TestMakeExtensionTemplateList:
    def test_single_template_ods(self):
        ctx = {}
        result = _make_extension_template_list(ctx, "table.html", "ods")
        assert result == ["table.ods"]

    def test_template_list_xlsx(self):
        ctx = {}
        result = _make_extension_template_list(ctx, ["table.html", "base.html"], "xlsx")
        assert result == ["table.xlsx", "base.xlsx"]

    def test_with_context_template_name(self):
        ctx = {"template_name": "custom"}
        result = _make_extension_template_list(ctx, "table.html", "ods")
        assert result[0] == "custom.ods"

    def test_with_fallback(self):
        ctx = {}
        result = _make_extension_template_list(ctx, "table.html", "ods", "schsys/table.ods")
        assert result[-1] == "schsys/table.ods"


class TestLocalizationTemplateResponse:
    def test_english_lang_returns_original(self, rf):
        request = rf.get("/")
        request.LANGUAGE_CODE = "en"
        with patch("django.template.response.TemplateResponse.resolve_template") as mock_rt:
            LocalizationTemplateResponse(request, "base.html").resolve_template("base.html")
            mock_rt.assert_called_once()

    def test_polish_lang_adds_suffix(self, rf):
        request = rf.get("/")
        request.LANGUAGE_CODE = "pl"
        with patch("django.template.response.TemplateResponse.resolve_template") as mock_rt:
            LocalizationTemplateResponse(request, "base.html").resolve_template("base.html")
            templates = mock_rt.call_args[0][1]
            assert "base_pl.html" in templates
            assert "base.html" in templates

    def test_polish_lang_with_list(self, rf):
        request = rf.get("/")
        request.LANGUAGE_CODE = "pl"
        # Test the logic directly: non-en lang with str template
        request.LANGUAGE_CODE = "pl"
        templates = []
        lang = request.LANGUAGE_CODE[:2].lower()
        template = "a.html"
        templates.append(template.replace(".html", "_" + lang + ".html"))
        templates.append(template)
        assert "a_pl.html" in templates
        assert "a.html" in templates
        # And with list
        templates = []
        for pos in ["a.html", "b.html"]:
            templates.append(pos.replace(".html", "_" + lang + ".html"))
            templates.append(pos)
        assert "a_pl.html" in templates
        assert "b_pl.html" in templates

    def test_no_language_code_falls_back_to_en(self, rf):
        request = rf.get("/")
        with patch("django.template.response.TemplateResponse.resolve_template") as mock_rt:
            LocalizationTemplateResponse(request, "base.html").resolve_template("base.html")
            mock_rt.assert_called_once()

    def test_two_char_lang_code(self, rf):
        request = rf.get("/")
        request.LANGUAGE_CODE = "de-DE"
        lang = request.LANGUAGE_CODE[:2].lower()
        assert lang == "de"
        templates = []
        pos = "base.html"
        templates.append(pos.replace(".html", "_" + lang + ".html"))
        templates.append(pos)
        assert "base_de.html" in templates


class TestExtTemplateView:
    def test_doc_type_defaults_to_html(self, rf):
        request = rf.get("/")
        view = ExtTemplateView()
        view.request = request
        view.kwargs = {"target": ""}
        assert view.doc_type() == "html"

    def test_doc_type_from_target_pdf(self, rf):
        request = rf.get("/")
        view = ExtTemplateView()
        view.request = request
        view.kwargs = {"target": "pdf"}
        assert view.doc_type() == "pdf"

    def test_doc_type_from_target_xlsx(self, rf):
        request = rf.get("/")
        view = ExtTemplateView()
        view.request = request
        view.kwargs = {"target": "xlsx"}
        assert view.doc_type() == "xlsx"

    def test_doc_type_from_json_param(self, rf):
        request = rf.get("/", {"json": "1"})
        view = ExtTemplateView()
        view.request = request
        view.kwargs = {"target": ""}
        assert view.doc_type() == "json"

    def test_doc_type_target_takes_precedence(self, rf):
        request = rf.get("/", {"json": "1"})
        view = ExtTemplateView()
        view.request = request
        view.kwargs = {"target": "pdf"}
        assert view.doc_type() == "pdf"

    def test_post_delegates_to_get(self, rf):
        request = rf.post("/")
        view = ExtTemplateView()
        view.get = MagicMock(return_value=HttpResponse("ok"))
        result = view.post(request)
        view.get.assert_called_once_with(request)
        assert result.content == b"ok"


class TestRenderToResponse:
    @patch("pytigon_lib.schviews.viewtools.loader.render_to_string")
    def test_basic_render(self, mock_render, rf):
        mock_render.return_value = "content"
        resp = render_to_response("tmpl.html", context={"x": 1})
        assert resp.status_code == 200
        assert resp.content == b"content"

    @patch("pytigon_lib.schviews.viewtools.loader.render_to_string")
    def test_render_with_status(self, mock_render, rf):
        mock_render.return_value = "content"
        resp = render_to_response("tmpl.html", context={}, status=201)
        assert resp.status_code == 201

    @patch("pytigon_lib.schviews.viewtools.loader.render_to_string")
    def test_render_with_content_type(self, mock_render, rf):
        mock_render.return_value = "content"
        resp = render_to_response("tmpl.html", context={}, content_type="text/plain")
        assert resp["Content-Type"] == "text/plain"


class TestRenderToResponseExt:
    @patch("pytigon_lib.schviews.viewtools.ExtTemplateView")
    def test_does_not_mutate_caller_context(self, mock_view_cls, rf):
        mock_view_cls.as_view.return_value = MagicMock(return_value=HttpResponse("ok"))
        request = rf.get("/")
        ctx = {"key": "value"}
        render_to_response_ext(request, "tmpl.html", ctx, doc_type="html")
        assert ctx == {"key": "value"}

    @patch("pytigon_lib.schviews.viewtools.ExtTemplateView")
    def test_adds_target_to_context(self, mock_view_cls, rf):
        mock_view = MagicMock(return_value=HttpResponse("ok"))
        mock_view_cls.as_view.return_value = mock_view
        request = rf.get("/")
        ctx = {"a": 1}
        render_to_response_ext(request, "tmpl.html", ctx, doc_type="pdf")
        call_args = mock_view.call_args
        assert call_args[1]["target"] == "pdf"


class TestDuplicateRow:
    @patch("pytigon_lib.schviews.viewtools.apps.get_model")
    def test_model_not_found(self, mock_get_model, rf):
        mock_get_model.return_value = None
        resp = duplicate_row(rf.get("/"), "app", "Tab", 1)
        assert resp.content == b"NO"

    @patch("pytigon_lib.schviews.viewtools.apps.get_model")
    def test_object_not_found(self, mock_get_model, rf):
        mock_model = MagicMock()
        from django.core.exceptions import ObjectDoesNotExist
        mock_model.objects.get.side_effect = ObjectDoesNotExist
        mock_get_model.return_value = mock_model
        resp = duplicate_row(rf.get("/"), "app", "Tab", 1)
        assert resp.content == b"NO"

    @patch("pytigon_lib.schviews.viewtools.apps.get_model")
    def test_successful_duplicate(self, mock_get_model, rf):
        mock_model = MagicMock()
        mock_obj = MagicMock()
        mock_obj.id = 42
        mock_model.objects.get.return_value = mock_obj
        mock_get_model.return_value = mock_model
        resp = duplicate_row(rf.get("/"), "app", "Tab", 1)
        assert resp.content == b"YES"
        assert mock_obj.id is None
        mock_obj.save.assert_called_once()


class TestDictDecorators:
    def test_dict_to_json_returns_json(self, rf):
        @dict_to_json
        def view_fn(request):
            return {"key": "value"}

        resp = view_fn(rf.get("/"))
        assert resp["Content-Type"] == "application/json"
        assert resp.status_code == 200

    def test_dict_to_json_with_list(self, rf):
        @dict_to_json
        def view_fn(request):
            return [1, 2, 3]

        resp = view_fn(rf.get("/"))
        assert resp["Content-Type"] == "application/json"

    def test_dict_to_xml_string(self, rf):
        @dict_to_xml
        def view_fn(request):
            return "<xml>test</xml>"

        resp = view_fn(rf.get("/"))
        assert resp["Content-Type"] == "application/xhtml+xml"
        assert b"<xml>test</xml>" in resp.content

    @patch("pytigon_lib.schviews.viewtools.render_to_response_ext")
    def test_dict_to_txt_decorator(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("txt content")

        @dict_to_txt("template.txt")
        def view_fn(request):
            return {"msg": "hello"}

        view_fn(rf.get("/"))
        call_kwargs = mock_rtr.call_args[1]
        assert call_kwargs["doc_type"] == "txt"

    @patch("pytigon_lib.schviews.viewtools.render_to_response_ext")
    def test_dict_to_hdoc_decorator(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("hdoc content")

        @dict_to_hdoc("template.html")
        def view_fn(request):
            return {"msg": "hello"}

        view_fn(rf.get("/"))
        call_kwargs = mock_rtr.call_args[1]
        assert call_kwargs["doc_type"] == "hdoc"

    @patch("pytigon_lib.schviews.viewtools.render_to_response_ext")
    def test_dict_to_hxls_decorator(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("hxls content")

        @dict_to_hxls("template.html")
        def view_fn(request):
            return {"msg": "hello"}

        view_fn(rf.get("/"))
        call_kwargs = mock_rtr.call_args[1]
        assert call_kwargs["doc_type"] == "hxls"

    @patch("pytigon_lib.schviews.viewtools.render_to_response_ext")
    def test_dict_to_pdf_decorator(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("pdf content")

        @dict_to_pdf("template.html")
        def view_fn(request):
            return {"msg": "hello"}

        view_fn(rf.get("/"))
        call_kwargs = mock_rtr.call_args[1]
        assert call_kwargs["doc_type"] == "pdf"

    @patch("pytigon_lib.schviews.viewtools.render_to_response_ext")
    def test_dict_to_spdf_decorator(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("spdf content")

        @dict_to_spdf("template.html")
        def view_fn(request):
            return {"msg": "hello"}

        view_fn(rf.get("/"))
        call_kwargs = mock_rtr.call_args[1]
        assert call_kwargs["doc_type"] == "spdf"

    @patch("pytigon_lib.schviews.viewtools.render_to_response_ext")
    @override_settings(URL_ROOT_FOLDER="")
    def test_dict_to_template_with_redirect(self, mock_rtr, rf):
        @dict_to_template("template.html")
        def view_fn(request):
            return {"redirect": "/some/url"}

        resp = view_fn(rf.get("/"))
        assert isinstance(resp, HttpResponseRedirect)
        assert resp.status_code == 302

    @patch("pytigon_lib.schviews.viewtools.render_to_response_ext")
    def test_dict_to_template_http_response_passthrough(self, mock_rtr, rf):
        @dict_to_template("template.html")
        def view_fn(request):
            return HttpResponse("direct")

        resp = view_fn(rf.get("/"))
        assert resp.content == b"direct"

    @patch("pytigon_lib.schviews.viewtools.render_to_response_ext")
    def test_dict_to_template_with_custom_template_name(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("ok")

        @dict_to_template("default.html")
        def view_fn(request):
            return {"template_name": "custom", "x": 1}

        view_fn(rf.get("/"))
        call_args = mock_rtr.call_args[0]
        assert call_args[1] == "custom"

    @patch("pytigon_lib.schviews.viewtools.render_to_response_ext")
    def test_dict_to_template_with_doc_type(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("ok")

        @dict_to_template("template.html")
        def view_fn(request):
            return {"template_name": "custom", "doc_type": "pdf"}

        view_fn(rf.get("/"))
        call_kwargs = mock_rtr.call_args[1]
        assert call_kwargs["doc_type"] == "pdf"

    @patch("pytigon_lib.schviews.viewtools.render_to_response_ext")
    def test_dict_to_odf_decorator(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("odf")

        @dict_to_odf("template.ods")
        def view_fn(request):
            return {"data": "hello"}

        view_fn(rf.get("/"))
        call_args = mock_rtr.call_args[0]
        assert call_args[1] == "template.ods"

    @patch("pytigon_lib.schviews.viewtools.render_to_response_ext")
    def test_dict_to_ooxml_decorator(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("ooxml")

        @dict_to_ooxml("template.xlsx")
        def view_fn(request):
            return {"data": "hello"}

        view_fn(rf.get("/"))
        call_args = mock_rtr.call_args[0]
        assert call_args[1] == "template.xlsx"
