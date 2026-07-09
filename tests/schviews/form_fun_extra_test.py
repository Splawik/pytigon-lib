from unittest.mock import MagicMock, patch

import pytest
from django import forms
from django.http import HttpResponse
from django.test import RequestFactory

from pytigon_lib.schviews.form_fun import (
    direct_to_template,
    form,
    form_with_perms,
    list_and_form,
)


class ValidForm(forms.Form):
    name = forms.CharField()

    def process(self, request):
        return {"msg": "processed"}


class InvalidForm(forms.Form):
    name = forms.CharField(required=True)


class EmptyProcessForm(forms.Form):
    name = forms.CharField(required=False)

    def process_empty(self, request):
        return {"msg": "empty"}


class PostProcessForm(forms.Form):
    name = forms.CharField()

    def process(self, request):
        return HttpResponse("custom_response")


class ProcessInvalidForm(forms.Form):
    name = forms.CharField(required=True, min_length=10)

    def process_invalid(self, request):
        return {"invalid_msg": "bad"}


@pytest.fixture
def rf():
    return RequestFactory()


class TestFormView:
    @patch("pytigon_lib.schviews.form_fun.render_to_response_ext")
    def test_valid_form_renders_ext(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("ok")
        request = rf.post("/", {"name": "test"})
        form(request, "test_app", ValidForm, "template.html")
        mock_rtr.assert_called_once()
        args = mock_rtr.call_args[0]
        assert args[1] == "template.html"

    @patch("pytigon_lib.schviews.form_fun.render_to_response")
    def test_invalid_form_renders_via_render_to_response(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("ok")
        request = rf.post("/", {})
        form(request, "test_app", InvalidForm, "template.html")
        mock_rtr.assert_called_once()
        args = mock_rtr.call_args[0]
        assert args[0] == "template.html"
        call_kwargs = mock_rtr.call_args[1]
        assert "form" in call_kwargs["context"]

    @patch("pytigon_lib.schviews.form_fun.render_to_response_ext")
    def test_form_with_object_id(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("ok")
        request = rf.post("/", {"name": "test"})
        form(request, "test_app", ValidForm, "template.html", object_id=42)
        mock_rtr.assert_called_once()
        ctx = mock_rtr.call_args[1]["context"]
        assert ctx.get("object_id") == 42

    def test_form_custom_response_passthrough(self, rf):
        request = rf.post("/", {"name": "test"})
        resp = form(request, "test_app", PostProcessForm, "template.html")
        assert resp.content == b"custom_response"
        assert resp.status_code == 200

    @patch("pytigon_lib.schviews.form_fun.render_to_response")
    def test_form_invalid_with_process_invalid(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("invalid")
        request = rf.post("/", {"name": "x"})
        form(request, "test_app", ProcessInvalidForm, "template.html")
        mock_rtr.assert_called_once()
        call_kwargs = mock_rtr.call_args[1]
        context = call_kwargs["context"]
        assert context.get("invalid_msg") == "bad"

    @patch("pytigon_lib.schviews.form_fun.render_to_response")
    def test_empty_form_with_process_empty(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("empty_ok")
        request = rf.get("/")
        form(request, "test_app", EmptyProcessForm, "template.html")
        mock_rtr.assert_called_once()
        call_kwargs = mock_rtr.call_args[1]
        context = call_kwargs["context"]
        assert context.get("form") is not None

    @patch("pytigon_lib.schviews.form_fun.render_to_response")
    def test_empty_form_no_post_no_process_empty(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("ok")

        class SimpleForm(forms.Form):
            name = forms.CharField(required=False)

        request = rf.get("/")
        form(request, "test_app", SimpleForm, "template.html")
        mock_rtr.assert_called_once()
        call_kwargs = mock_rtr.call_args[1]
        assert "form" in call_kwargs["context"]


class TestListAndForm:
    @patch("pytigon_lib.schviews.form_fun.render_to_response")
    def test_get_request_renders_template(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("ok")

        class SimpleForm(forms.Form):
            name = forms.CharField(required=False)

        request = rf.get("/")
        mock_qs = MagicMock()
        list_and_form(request, mock_qs, SimpleForm, "template.html")
        mock_rtr.assert_called_once()
        context = mock_rtr.call_args[1]["context"]
        assert "object_list" in context
        assert "form" in context

    @patch("pytigon_lib.schviews.form_fun.render_to_response")
    def test_post_valid_form_calls_process(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("ok")

        class FilterForm(forms.Form):
            name = forms.CharField()

            def process(self, request, queryset):
                return queryset

        request = rf.post("/", {"name": "test"})
        mock_qs = MagicMock()
        list_and_form(request, mock_qs, FilterForm, "template.html")
        context = mock_rtr.call_args[1]["context"]
        assert "form" in context

    @patch("pytigon_lib.schviews.form_fun.render_to_response")
    def test_list_and_form_with_extra_context(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("ok")

        class SimpleForm(forms.Form):
            name = forms.CharField(required=False)

        request = rf.get("/")
        mock_qs = MagicMock()
        list_and_form(
            request, mock_qs, SimpleForm, "template.html", extra_context={"custom": "value"}
        )
        context = mock_rtr.call_args[1]["context"]
        assert context["custom"] == "value"

    @patch("pytigon_lib.schviews.form_fun.render_to_response")
    def test_list_and_form_table_always_true_calls_process_empty(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("ok")

        class FormWithEmpty(forms.Form):
            name = forms.CharField(required=False)

            def process_empty(self, request, queryset):
                queryset.filtered = True
                return queryset

        request = rf.get("/")
        mock_qs = MagicMock()
        list_and_form(request, mock_qs, FormWithEmpty, "template.html", table_always=True)
        mock_rtr.assert_called_once()
        context = mock_rtr.call_args[1]["context"]
        assert "form" in context


class TestDirectToTemplate:
    @patch("pytigon_lib.schviews.form_fun.render_to_response")
    def test_basic_rendering(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("ok")
        request = rf.get("/")
        direct_to_template(request, "template.html")
        mock_rtr.assert_called_once()
        args = mock_rtr.call_args[0]
        assert args[0] == "template.html"

    @patch("pytigon_lib.schviews.form_fun.render_to_response")
    def test_kwargs_in_params(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("ok")
        request = rf.get("/")
        direct_to_template(request, "template.html", x=1, y=2)
        call_kwargs = mock_rtr.call_args[1]
        assert call_kwargs["context"]["params"] == {"x": 1, "y": 2}

    @patch("pytigon_lib.schviews.form_fun.render_to_response")
    def test_extra_context_merges(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("ok")
        request = rf.get("/")
        direct_to_template(request, "template.html", extra_context={"z": "value"})
        call_kwargs = mock_rtr.call_args[1]
        assert call_kwargs["context"]["z"] == "value"

    @patch("pytigon_lib.schviews.form_fun.render_to_response")
    def test_extra_context_with_callables(self, mock_rtr, rf):
        mock_rtr.return_value = HttpResponse("ok")
        request = rf.get("/")

        def compute_value():
            return 42

        direct_to_template(request, "template.html", extra_context={"computed": compute_value})
        call_kwargs = mock_rtr.call_args[1]
        assert call_kwargs["context"]["computed"] == 42


class TestFormWithPerms:
    @patch("pytigon_lib.schviews.form_fun.make_perms_url_test_fun")
    def test_calls_perms_wrapper(self, mock_make_perms):
        form_with_perms("myapp")
        mock_make_perms.assert_called_once_with("myapp", form)


class TestFormExceptions:
    def test_exception_returns_500(self, rf):
        class BadForm(forms.Form):
            name = forms.CharField()

            def preprocess_request(self, req):
                raise RuntimeError("boom")

        request = rf.post("/", {"name": "test"})
        resp = form(request, "test_app", BadForm, "template.html")
        assert resp.status_code == 500
