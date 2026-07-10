import datetime
from unittest.mock import MagicMock, patch

import django
import pytest
from django.http import HttpResponse
from django.test import RequestFactory, override_settings

from pytigon_lib.schviews import (
    VIEWS_REGISTER,
    GenericTable,
    convert_str_to_model_field,
    extend_generic_view,
    gen_row_action,
    gen_tab_action,
    gen_tab_field_action,
    generic_table_start,
    make_path,
    save,
    transform_extra_context,
    view_editor,
)


@pytest.fixture
def rf():
    return RequestFactory()


class TestMakePath:
    @patch("pytigon_lib.schviews._utils.reverse")
    @override_settings(URL_ROOT_FOLDER="")
    def test_no_root_folder(self, mock_reverse, rf):
        mock_reverse.return_value = "/path/"
        result = make_path("view_name")
        assert result == "/path/"

    @patch("pytigon_lib.schviews._utils.reverse")
    @override_settings(URL_ROOT_FOLDER="/root")
    def test_with_root_folder(self, mock_reverse, rf):
        mock_reverse.return_value = "path/"
        result = make_path("view_name")
        assert result.startswith("/root/")
        assert "path/" in result

    @patch("pytigon_lib.schviews._utils.reverse")
    @override_settings(URL_ROOT_FOLDER="")
    def test_with_args(self, mock_reverse, rf):
        mock_reverse.return_value = "/path/1/"
        result = make_path("view_name", args=[1])
        assert result == "/path/1/"


class TestConvertStrToModelField:
    def test_charfield_returns_string(self):
        field = MagicMock(spec=django.db.models.CharField)
        result = convert_str_to_model_field("hello", field)
        assert result == "hello"

    def test_textfield_returns_string(self):
        field = MagicMock(spec=django.db.models.TextField)
        result = convert_str_to_model_field("world", field)
        assert result == "world"

    def test_integerfield_returns_int(self):
        field = MagicMock(spec=django.db.models.IntegerField)
        result = convert_str_to_model_field("42", field)
        assert result == 42
        assert isinstance(result, int)

    def test_bigautofield_returns_int(self):
        field = MagicMock(spec=django.db.models.BigAutoField)
        result = convert_str_to_model_field("99", field)
        assert result == 99

    def test_floatfield_returns_float(self):
        field = MagicMock(spec=django.db.models.FloatField)
        result = convert_str_to_model_field("3.14", field)
        assert result == 3.14
        assert isinstance(result, float)

    def test_datetimefield_returns_datetime(self):
        field = MagicMock(spec=django.db.models.DateTimeField)
        result = convert_str_to_model_field("2024-01-15T12:30:00+00:00", field)
        assert isinstance(result, datetime.datetime)
        assert result.year == 2024
        assert result.month == 1

    def test_datefield_returns_date(self):
        field = MagicMock(spec=django.db.models.DateField)
        result = convert_str_to_model_field("2024-06-15", field)
        assert isinstance(result, datetime.date)
        assert result.year == 2024
        assert result.month == 6

    def test_booleanfield_true(self):
        field = MagicMock(spec=django.db.models.BooleanField)
        assert convert_str_to_model_field("True", field) is True
        assert convert_str_to_model_field("1", field) is True
        assert convert_str_to_model_field("anything", field) is True

    def test_booleanfield_false(self):
        field = MagicMock(spec=django.db.models.BooleanField)
        assert convert_str_to_model_field("0", field) is False
        assert convert_str_to_model_field("False", field) is False


class TestTransformExtraContext:
    def test_none_returns_original(self):
        ctx = {"a": 1}
        result = transform_extra_context(ctx, None)
        assert result is ctx
        assert result == {"a": 1}

    def test_plain_values_merge(self):
        ctx = {"a": 1}
        result = transform_extra_context(ctx, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_callables_are_called(self):
        ctx = {"a": 1}

        def compute():
            return 42

        result = transform_extra_context(ctx, {"b": compute})
        assert result["b"] == 42

    def test_mutates_original_dict(self):
        ctx = {"a": 1}
        result = transform_extra_context(ctx, {"b": 2})
        assert result is ctx
        assert ctx["b"] == 2

    def test_overwrites_existing_keys(self):
        ctx = {"a": 1}
        result = transform_extra_context(ctx, {"a": "new"})
        assert result["a"] == "new"


class TestSave:
    def test_save_from_request_called(self):
        mock_obj = MagicMock()
        mock_obj.save_from_request.assert_not_called()  # sanity
        save(mock_obj, "request", "edit", {"param": 1})
        mock_obj.save_from_request.assert_called_once_with("request", "edit", {"param": 1})
        mock_obj.save.assert_not_called()

    def test_plain_save_when_no_method(self):
        mock_obj = MagicMock()
        del mock_obj.save_from_request
        mock_obj.save = MagicMock()
        save(mock_obj, "request", "edit")
        mock_obj.save.assert_called_once()


class TestViewEditor:
    def setup_method(self):
        self.mock_model = MagicMock()
        self.mock_obj = MagicMock()
        self.mock_obj._meta.fields = []
        self.mock_model.objects.get.return_value = self.mock_obj

    @patch("pytigon_lib.schviews.is_rules_active", return_value=False)
    def test_post_sets_value_returns_ok(self, mock_ira, rf):
        request = rf.post("/", {"value": "new_value", "pk": "1"})
        result = view_editor(
            request, pk=1, app="myapp", tab="MyTab", model=self.mock_model,
            template_name="t.html", field_edit_name="body",
            post_save_redirect="/ok", target="editable",
        )
        assert result.status_code == 200
        assert result.content == b"OK"

    @patch("pytigon_lib.schviews.is_rules_active", return_value=False)
    @patch("pytigon_lib.schviews.render_to_response")
    def test_get_renders_template(self, mock_rtr, mock_ira, rf):
        mock_rtr.return_value = HttpResponse("editor page")
        request = rf.get("/")
        view_editor(
            request, pk=1, app="myapp", tab="MyTab", model=self.mock_model,
            template_name="t.html", field_edit_name="body",
            post_save_redirect="/ok",
        )
        mock_rtr.assert_called_once()
        context = mock_rtr.call_args[1]["context"]
        assert context["app"] == "myapp"
        assert context["pk"] == 1

    @patch("pytigon_lib.schviews.is_rules_active", return_value=False)
    def test_get_with_fragment_header(self, mock_ira, rf):
        self.mock_obj.body = "header$$$footer"
        request = rf.get("/?fragment=header")
        with patch("pytigon_lib.schviews.render_to_response") as mock_rtr:
            mock_rtr.return_value = HttpResponse("ok")
            view_editor(
                request, pk=1, app="myapp", tab="MyTab", model=self.mock_model,
                template_name="t.html", field_edit_name="body",
                post_save_redirect="/ok",
            )
            context = mock_rtr.call_args[1]["context"]
            assert context["txt"] == "header"

    @patch("pytigon_lib.schviews.is_rules_active", return_value=False)
    def test_get_with_fragment_footer(self, mock_ira, rf):
        self.mock_obj.body = "header$$$footer"
        request = rf.get("/?fragment=footer")
        with patch("pytigon_lib.schviews.render_to_response") as mock_rtr:
            mock_rtr.return_value = HttpResponse("ok")
            view_editor(
                request, pk=1, app="myapp", tab="MyTab", model=self.mock_model,
                template_name="t.html", field_edit_name="body",
                post_save_redirect="/ok",
            )
            context = mock_rtr.call_args[1]["context"]
            assert context["txt"] == "footer"

    @patch("pytigon_lib.schviews.is_rules_active", return_value=False)
    def test_post_save_with_data(self, mock_ira, rf):
        self.mock_obj.body = ""
        request = rf.post("/", {"data": "full_content"})
        with patch("pytigon_lib.schviews.save"):
            view_editor(
                request, pk=1, app="myapp", tab="MyTab", model=self.mock_model,
                template_name="t.html", field_edit_name="body",
                post_save_redirect="/ok",
            )
            assert self.mock_obj.body == "full_content"


class TestGenTabAction:
    def test_generates_path_object(self):
        mock_fun = MagicMock()
        result = gen_tab_action("users", "export", mock_fun)
        assert hasattr(result, "pattern")

    def test_generates_correct_name(self):
        mock_fun = MagicMock()
        result = gen_tab_action("UserProfile", "export", mock_fun)
        assert result.name == "tab_action_userprofile_export"


class TestGenRowAction:
    def test_generates_path_object(self):
        mock_fun = MagicMock()
        result = gen_row_action("users", "ban", mock_fun)
        assert hasattr(result, "pattern")

    def test_generates_correct_name(self):
        mock_fun = MagicMock()
        result = gen_row_action("UserProfile", "reset_password", mock_fun)
        assert result.name == "row_action_userprofile_reset_password"


class TestGenTabFieldAction:
    def test_generates_path_object(self):
        mock_fun = MagicMock()
        result = gen_tab_field_action("users", "comments", "moderate", mock_fun)
        assert hasattr(result, "pattern")


class TestViewsRegister:
    def test_views_register_has_expected_keys(self):
        assert "list" in VIEWS_REGISTER
        assert "detail" in VIEWS_REGISTER
        assert "edit" in VIEWS_REGISTER
        assert "create" in VIEWS_REGISTER
        assert "delete" in VIEWS_REGISTER


class TestExtendGenericView:
    def test_extends_nonexistent_view_returns_none(self):
        mock_model = object()
        result = extend_generic_view("list", mock_model, "get_queryset", lambda self: [])
        assert result is None

    def test_extends_existing_view_no_old_method(self):
        mock_model = MagicMock()
        mock_cls = MagicMock()
        mock_cls.get_queryset = None

        register = {"list": {mock_model: mock_cls}, "detail": {}, "edit": {}, "create": {}, "delete": {}}
        with patch("pytigon_lib.schviews.VIEWS_REGISTER", register):
            def new_method(self):
                return "new"
            extend_generic_view("list", mock_model, "get_queryset", new_method)
            assert mock_cls.get_queryset is new_method

    def test_extends_stores_old_method(self):
        mock_model = MagicMock()
        mock_cls = MagicMock()

        def old_method(self):
            return "old"

        mock_cls.get_queryset = old_method

        register = {"list": {mock_model: mock_cls}, "detail": {}, "edit": {}, "create": {}, "delete": {}}
        with patch("pytigon_lib.schviews.VIEWS_REGISTER", register):
            def new_method(self):
                return "new"
            extend_generic_view("list", mock_model, "get_queryset", new_method)
            assert mock_cls.get_queryset is new_method
            assert hasattr(mock_cls, "old_get_queryset")


class TestGenericTable:
    def test_init(self):
        urlpatterns = []
        gt = GenericTable(urlpatterns, "myapp")
        assert gt.urlpatterns is urlpatterns
        assert gt.app == "myapp"
        assert gt.views_module is None

    def test_append_from_schema(self):
        urlpatterns = []
        gt = GenericTable(urlpatterns, "myapp")
        mock_rows = MagicMock()
        gt.append_from_schema(mock_rows, "a;b;c")
        assert mock_rows.a.called
        assert mock_rows.b.called
        assert mock_rows.c.called



class TestGenericTableStart:
    def test_returns_generic_table(self):
        urlpatterns = []
        result = generic_table_start(urlpatterns, "myapp")
        assert isinstance(result, GenericTable)
        assert result.app == "myapp"
        assert result.urlpatterns is urlpatterns
