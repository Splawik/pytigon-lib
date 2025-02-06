from itertools import chain
from django.forms.widgets import (
    CheckboxSelectMultiple,
    CheckboxInput,
    RadioSelect,
    TextInput,
    TimeInput,
)
from django.utils.safestring import mark_safe
from django.utils.html import conditional_escape, format_html, html_safe
from django.utils.encoding import force_str


@html_safe
class SubWidget:
    """
    Represents the "inner" HTML element of a widget, used for widgets like RadioSelect.
    """

    def __init__(self, parent_widget, name, value, attrs, choices):
        self.parent_widget = parent_widget
        self.name = name
        self.value = value
        self.attrs = attrs
        self.choices = choices

    def __str__(self):
        args = [self.name, self.value, self.attrs]
        if self.choices:
            args.append(self.choices)
        return self.parent_widget.render(*args)


@html_safe
class ChoiceInput(SubWidget):
    """
    Represents a single <input type='$input_type'> element used by ChoiceFieldRenderer.
    """

    input_type = None  # Subclasses must define this

    def __init__(self, name, value, attrs, choice, index):
        self.name = name
        self.value = value
        self.attrs = attrs
        self.choice_value = force_str(choice[0])
        self.choice_label = force_str(choice[1])
        self.index = index
        if "id" in self.attrs:
            self.attrs["id"] += f"_{self.index}"

    def __str__(self):
        return self.render()

    def render(self, name=None, value=None, attrs=None):
        label_for = (
            format_html(' for="{}"', self.id_for_label) if self.id_for_label else ""
        )
        attrs = dict(self.attrs, **(attrs or {}))
        return format_html(
            "<label{}>{} {}</label>", label_for, self.tag(attrs), self.choice_label
        )

    def is_checked(self):
        return self.value == self.choice_value

    def tag(self, attrs=None):
        attrs = attrs or self.attrs
        final_attrs = dict(
            attrs, type=self.input_type, name=self.name, value=self.choice_value
        )
        if self.is_checked():
            final_attrs["checked"] = "checked"
        return format_html("<input{} />", flatatt(final_attrs))

    @property
    def id_for_label(self):
        return self.attrs.get("id", "")


class RadioChoiceInput(ChoiceInput):
    input_type = "radio"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.value = force_str(self.value)


class CheckboxSelectMultipleWithIcon(CheckboxSelectMultiple):
    def render(self, name, value, attrs=None, renderer=None, choices=()):
        if value is None:
            value = []
        has_id = attrs and "id" in attrs
        final_attrs = self.build_attrs(attrs)
        output = ["<ul>"]
        str_values = {str(v) for v in value}

        for i, (option_value, option_label) in enumerate(chain(self.choices, choices)):
            if has_id:
                final_attrs = dict(final_attrs, id=f"{attrs['id']}_{i}")
                label_for = f' for="{final_attrs["id"]}"'
            else:
                label_for = ""

            cb = CheckboxInput(
                final_attrs, check_test=lambda value: str(value) in str_values
            )
            rendered_cb = cb.render(name, option_value)
            option_label = conditional_escape(option_label)
            parts = option_label.split("|")
            icon = parts[0] if len(parts) > 1 else None
            option_label = parts[1] if len(parts) > 1 else parts[0]
            image = f"<img src='{icon}' />" if icon else ""

            output.append(
                f"<li><label{label_for}>{rendered_cb} {image} {option_label}</label></li>"
            )

        output.append("</ul>")
        return mark_safe("\n".join(output))


class RadioInput2(RadioChoiceInput):
    def __str__(self):
        label_for = (
            f' for="{self.attrs["id"]}_{self.index}"' if "id" in self.attrs else ""
        )
        choice_label = conditional_escape(self.choice_label)
        parts = choice_label.split("|")
        label = (
            f"<img src='{parts[0]}' /> &nbsp; {parts[1]}"
            if len(parts) > 1
            else parts[0]
        )
        self.attrs["class"] = "radioselectwithicon"
        return mark_safe(f"<div><label>{self.tag()} {label}</label></div>")


class RadioFieldRendererWithIcon:
    """
    Enables customization of radio widgets used by RadioSelect.
    """

    def __init__(self, name, value, attrs, choices):
        self.name = name
        self.value = value
        self.attrs = attrs
        self.choices = choices

    def __iter__(self):
        for i, choice in enumerate(self.choices):
            yield RadioInput2(self.name, self.value, self.attrs.copy(), choice, i)

    def __getitem__(self, idx):
        choice = self.choices[idx]
        return RadioInput2(self.name, self.value, self.attrs.copy(), choice, idx)

    def __str__(self):
        return self.render()

    def render(self):
        return mark_safe(
            f"<ul class='radio' width=\"100%\">{' '.join(f'<li li-symbol="">{w}</li>' for w in self)}</ul>"
        )


class RadioSelectWithIcon(RadioSelect):
    renderer = RadioFieldRendererWithIcon
