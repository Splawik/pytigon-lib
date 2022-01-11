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


@html_safe
class SubWidget(object):
    """
    Some widgets are made of multiple HTML elements -- namely, RadioSelect.
    This is a class that represents the "inner" HTML element of a widget.
    """

    def __init__(self, parent_widget, name, value, attrs, choices):
        self.parent_widget = parent_widget
        self.name, self.value = name, value
        self.attrs, self.choices = attrs, choices

    def __str__(self):
        args = [self.name, self.value, self.attrs]
        if self.choices:
            args.append(self.choices)
        return self.parent_widget.render(*args)


@html_safe
class ChoiceInput(SubWidget):
    """
    An object used by ChoiceFieldRenderer that represents a single
    <input type='$input_type'>.
    """

    input_type = None  # Subclasses must define this

    def __init__(self, name, value, attrs, choice, index):
        self.name = name
        self.value = value
        self.attrs = attrs
        self.choice_value = force_text(choice[0])
        self.choice_label = force_text(choice[1])
        self.index = index
        if "id" in self.attrs:
            self.attrs["id"] += "_%d" % self.index

    def __str__(self):
        return self.render()

    def render(self, name=None, value=None, attrs=None):
        if self.id_for_label:
            label_for = format_html(' for="{}"', self.id_for_label)
        else:
            label_for = ""
        attrs = dict(self.attrs, **attrs) if attrs else self.attrs
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
        super(RadioChoiceInput, self).__init__(*args, **kwargs)
        self.value = force_text(self.value)


class CheckboxSelectMultipleWithIcon(CheckboxSelectMultiple):
    def render(self, name, value, attrs=None, renderer=None, choices=()):
        if value is None:
            value = []
        has_id = attrs and "id" in attrs
        final_attrs = self.build_attrs(attrs)
        output = ["<ul>"]
        str_values = set([str(v) for v in value])
        for (i, (option_value, option_label)) in enumerate(
            chain(self.choices, choices)
        ):
            if has_id:
                final_attrs = dict(final_attrs, id="%s_%s" % (attrs["id"], i))
                label_for = ' for="%s"' % final_attrs["id"]
            else:
                label_for = ""
            cb = CheckboxInput(
                final_attrs, check_test=lambda value: str(value) in str_values
            )
            rendered_cb = cb.render(name, option_value)
            option_label = conditional_escape(option_label)
            x = option_label.split("|")
            if len(x) > 1:
                icon = x[0]
                option_label = x[1]
            else:
                icon = None
            if icon:
                image = "<img src='%s' />" % icon
            else:
                image = ""
            output.append(
                "<li><label%s>%s %s %s</label></li>"
                % (label_for, rendered_cb, image, option_label)
            )
        output.append("</ul>")
        return mark_safe("\n".join(output))


class RadioInput2(RadioChoiceInput):
    def __str__(self):
        if "id" in self.attrs:
            label_for = ' for="%s_%s"' % (self.attrs["id"], self.index)
        else:
            label_for = ""
        choice_label = conditional_escape(self.choice_label)
        x = choice_label.split("|")
        if len(x) > 1:
            label = "<img src='%s' /> &nbsp; " % x[0] + x[1]
        else:
            label = x[0]
        self.attrs["class"] = "radioselectwithicon"
        return mark_safe("<div><label>%s %s</label></div>" % (self.tag(), label))


class RadioFieldRendererWithIcon(object):
    """An object used by RadioSelect to enable customization of radio widgets."""

    def __init__(self, name, value, attrs, choices):
        (self.name, self.value, self.attrs) = (name, value, attrs)
        self.choices = choices

    def __iter__(self):
        for (i, choice) in enumerate(self.choices):
            yield RadioInput2(self.name, self.value, self.attrs.copy(), choice, i)

    def __getitem__(self, idx):
        choice = self.choices[idx]
        return RadioInput2(self.name, self.value, self.attrs.copy(), choice, idx)

    def __str__(self):
        return self.render()

    def render(self):
        """Outputs a <ul> for this set of radio fields."""
        return mark_safe(
            "<ul class='radio' width=\"100%%\">%s</ul>"
            % " ".join(['<li li-symbol="">%s</li>' % w for w in self])
        )


class RadioSelectWithIcon(RadioSelect):
    renderer = RadioFieldRendererWithIcon
