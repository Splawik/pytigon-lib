from unittest.mock import patch

import pytest
from django import forms

from pytigon_lib.schdjangoext.fastform import (
    _get_name_and_title,
    _read_form_line,
    _safe_exec_form,
    _scan_lines,
    form_from_str,
)


class TestScanLines:
    def test_single_line(self):
        result = _scan_lines("Name::****")
        assert result == ["Name::****"]

    def test_multiple_lines(self):
        result = _scan_lines("Name::****\nAge::000")
        assert result == ["Name::****", "Age::000"]

    def test_multiline_choices(self):
        result = _scan_lines("Choose::[option1;option2\noption3]")
        assert result == ["Choose::[option1;option2;option3]"]

    def test_multiline_choices_across_multiple(self):
        result = _scan_lines("Choose::[a;b\nc\nd]")
        assert result == ["Choose::[a;b;c;d]"]

    def test_empty_lines_ignored(self):
        result = _scan_lines("\nName::****\n\nAge::000\n")
        assert result == ["", "Name::****", "", "Age::000", ""]

    def test_closed_brackets_no_continuation(self):
        result = _scan_lines("Choose::[a;b]\nName::****")
        assert result == ["Choose::[a;b]", "Name::****"]


class TestGetNameAndTitle:
    def test_simple_name(self):
        name, title, required = _get_name_and_title("Name")
        assert title == "Name"
        assert required is False
        assert name == "name"

    def test_required_field(self):
        name, title, required = _get_name_and_title("Name!")
        assert title == "Name"
        assert required is True

    def test_explicit_name(self):
        name, title, required = _get_name_and_title("fld//Title")
        assert name == "fld"
        assert title == "Title"
        assert required is False

    def test_explicit_name_required(self):
        name, title, required = _get_name_and_title("fld//Title!")
        assert name == "fld"
        assert title == "Title"
        assert required is True

    def test_name_truncation(self):
        name, title, required = _get_name_and_title("Very Long Name That Exceeds Sixteen Characters")
        assert len(name) <= 16


class TestReadFormLine:
    def test_charfield(self):
        name, ftype, title, required, kwargs = _read_form_line("Name::****")
        assert ftype is forms.CharField
        assert kwargs["max_length"] == 4

    def test_integerfield(self):
        name, ftype, title, required, kwargs = _read_form_line("Age::000")
        assert ftype is forms.IntegerField
        assert kwargs["min_value"] == 0
        assert kwargs["max_value"] == 1000

    def test_floatfield(self):
        name, ftype, title, required, kwargs = _read_form_line("Amount::99")
        assert ftype is forms.FloatField
        assert kwargs["min_value"] == 0
        assert kwargs["max_value"] == 100

    def test_datefield(self):
        name, ftype, title, required, kwargs = _read_form_line("Date::####.##.##")
        assert ftype is forms.DateField

    def test_textarea(self):
        name, ftype, title, required, kwargs = _read_form_line("Description::_")
        assert ftype is forms.CharField
        assert kwargs["widget"] is forms.Textarea

    def test_choicefield(self):
        name, ftype, title, required, kwargs = _read_form_line("Choose::[a;b;c]")
        assert ftype is forms.ChoiceField
        assert kwargs["choices"] == [("a", "a"), ("b", "b"), ("c", "c")]

    def test_boolean_field(self):
        name, ftype, title, required, kwargs = _read_form_line("Active?")
        assert ftype is forms.BooleanField

    def test_default_charfield(self):
        name, ftype, title, required, kwargs = _read_form_line("PlainField")
        assert ftype is forms.CharField


class TestFormFromStrExtra:
    def test_code_syntax_mode(self):
        form_str = "make_form_class\ndef make_form_class(base_form, init_data):\n    class form_class(base_form):\n        pass\n    return form_class\n"
        with patch("pytigon_lib.schdjangoext.fastform._safe_exec_form") as mock_exec:
            mock_exec.side_effect = lambda src, gl, ln: ln.update({"make_form_class": lambda base, init: base})
            form_cls = form_from_str(form_str)
            mock_exec.assert_called_once()

    def test_form_with_prefix(self):
        form_str = "Name::****"
        form_cls = form_from_str(form_str, prefix="pfx_")
        form = form_cls()
        assert "pfx_name" in form.fields

    def test_form_with_empty_lines_skipped(self):
        form_str = "\n\nName::****\n\n"
        form_cls = form_from_str(form_str)
        form = form_cls()
        assert "name" in form.fields

    def test_form_single_integer_valid(self):
        form_str = "Count::0000"
        form_cls = form_from_str(form_str)
        form = form_cls(data={"count": "9999"})
        assert form.is_valid()

    def test_form_date_field_renders(self):
        form_str = "StartDate::####-##-##"
        form_cls = form_from_str(form_str)
        form = form_cls()
        assert "startdate" in form.fields
