from unittest.mock import MagicMock, patch

import pytest
from django.forms.utils import flatatt
from django.forms.widgets import CheckboxInput
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from pytigon_lib.schdjangoext.formwidgets import (
    CheckboxSelectMultipleWithIcon,
    ChoiceInput,
    RadioChoiceInput,
    RadioFieldRendererWithIcon,
    RadioInput2,
    RadioSelectWithIcon,
    SubWidget,
)


class TestSubWidget:
    def test_init(self):
        parent = MagicMock()
        sub = SubWidget(parent, "myname", "myval", {"id": "test"}, [("a", "A")])
        assert sub.parent_widget is parent
        assert sub.name == "myname"
        assert sub.value == "myval"
        assert sub.attrs == {"id": "test"}
        assert sub.choices == [("a", "A")]

    def test_str_calls_parent_render(self):
        parent = MagicMock()
        parent.render.return_value = "rendered"
        sub = SubWidget(parent, "name", "val", {}, None)
        result = str(sub)
        parent.render.assert_called_once()
        assert result == "rendered"

    def test_is_html_safe(self):
        assert hasattr(SubWidget, "__html__")


class TestChoiceInput:
    def test_init_basic(self):
        ci = ChoiceInput("name", "a", {"id": "test"}, ("a", "Option A"), 0)
        assert ci.choice_value == "a"
        assert ci.choice_label == "Option A"
        assert ci.index == 0
        assert ci.attrs["id"] == "test_0"

    def test_is_checked_true(self):
        ci = ChoiceInput("name", "a", {}, ("a", "A"), 0)
        assert ci.is_checked() is True

    def test_is_checked_false(self):
        ci = ChoiceInput("name", "b", {}, ("a", "A"), 0)
        assert ci.is_checked() is False

    def test_tag_has_required_attributes(self):
        ci = ChoiceInput("name", "a", {}, ("a", "A"), 0)
        tag = ci.tag()
        assert "name=" in tag
        assert "value=" in tag
        assert "a" in tag

    def test_tag_checked(self):
        ci = ChoiceInput("name", "a", {}, ("a", "A"), 0)
        tag = ci.tag()
        assert tag is not None

    def test_id_for_label(self):
        ci = ChoiceInput("name", "a", {"id": "myid"}, ("a", "A"), 0)
        assert ci.id_for_label == "myid_0"

    def test_id_for_label_none(self):
        ci = ChoiceInput("name", "a", {}, ("a", "A"), 0)
        assert ci.id_for_label == ""


class TestRadioChoiceInput:
    def test_input_type(self):
        assert RadioChoiceInput.input_type == "radio"

    def test_value_is_forced_string(self):
        rci = RadioChoiceInput("name", 42, {}, ("42", "Label"), 0)
        assert rci.value == "42"
        assert isinstance(rci.value, str)


class TestCheckboxSelectMultipleWithIcon:
    def test_render_basic(self):
        widget = CheckboxSelectMultipleWithIcon()
        html = widget.render("test", ["a"], attrs={}, choices=[("a", "Option A")])
        assert "<ul>" in html
        assert "</ul>" in html
        assert "Option A" in html

    def test_render_with_icon(self):
        widget = CheckboxSelectMultipleWithIcon()
        html = widget.render("test", [], attrs={}, choices=[("/img/icon.png|Label with icon", "/img/icon.png|Label with icon")])
        assert "<img src='/img/icon.png'" in html
        assert "Label with icon" in html

    def test_render_no_icon(self):
        widget = CheckboxSelectMultipleWithIcon()
        html = widget.render("test", [], attrs={}, choices=[("Plain Label", "Plain Label")])
        assert "Plain Label" in html

    def test_render_none_value(self):
        widget = CheckboxSelectMultipleWithIcon()
        html = widget.render("test", None, attrs={}, choices=[])
        assert "<ul>" in html

    def test_render_with_id_attr(self):
        widget = CheckboxSelectMultipleWithIcon()
        html = widget.render("test", [], attrs={"id": "myid"}, choices=[("a", "A")])
        assert 'id="myid_0"' in html


class TestRadioInput2:
    def test_str_no_pipe(self):
        ri = RadioInput2("name", "a", {}, ("a", "Plain Label"), 0)
        result = str(ri)
        assert "Plain Label" in result

    def test_str_with_pipe(self):
        ri = RadioInput2("name", "a", {}, ("a", "/img/icon.png|Label"), 0)
        result = str(ri)
        assert "<img src='/img/icon.png'" in result
        assert "Label" in result

    def test_has_radioselectwithicon_class(self):
        ri = RadioInput2("name", "a", {}, ("a", "Label"), 0)
        result = str(ri)
        assert "radioselectwithicon" in result


class TestRadioFieldRendererWithIcon:
    def test_init(self):
        renderer = RadioFieldRendererWithIcon("name", "a", {}, [("a", "A"), ("b", "B")])
        assert renderer.name == "name"
        assert renderer.value == "a"

    def test_iter_yields_radio_inputs(self):
        renderer = RadioFieldRendererWithIcon("name", "a", {}, [("a", "A"), ("b", "B")])
        items = list(renderer)
        assert len(items) == 2
        assert all(isinstance(item, RadioInput2) for item in items)

    def test_getitem(self):
        renderer = RadioFieldRendererWithIcon("name", "a", {}, [("a", "A"), ("b", "B")])
        item = renderer[1]
        assert isinstance(item, RadioInput2)

    def test_render_produces_html(self):
        renderer = RadioFieldRendererWithIcon("name", "a", {}, [("a", "A")])
        html = renderer.render()
        assert "<ul" in html
        assert "</ul>" in html
        assert 'li-symbol=""' in html

    def test_str_calls_render(self):
        renderer = RadioFieldRendererWithIcon("name", "a", {}, [("a", "A")])
        result = str(renderer)
        assert "<ul" in result


class TestRadioSelectWithIcon:
    def test_renderer_is_custom(self):
        widget = RadioSelectWithIcon()
        assert widget.renderer is RadioFieldRendererWithIcon
