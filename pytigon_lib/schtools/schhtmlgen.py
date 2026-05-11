"""Lightweight HTML element tree and ihtml template rendering."""

from django.template import Template, Context
from pytigon_lib.schindent.indent_style import ihtml_to_html_base


class Html:
    """Represents an HTML element as a tree node.

    Supports nested children, attributes, and callable or static values.
    Use :meth:`dump` to render the full HTML string.
    """

    def __init__(self, name, attr=None):
        """Initialize an HTML element.

        Args:
            name: The HTML tag name (e.g. 'div', 'span').
            attr: Optional attribute string.
        """
        self.name = name
        self.attr = attr
        self.value = None
        self.children = []

    def setvalue(self, value):
        """Set the inner content of this element.

        Args:
            value: A string or callable that returns a string.
        """
        self.value = value

    def setattr(self, attr):
        """Set the HTML attributes string.

        Args:
            attr: Attribute string (e.g. 'class="foo" id="bar"').
        """
        self.attr = attr

    def append(self, elem, attr=None):
        """Append a child element.

        Args:
            elem: An Html instance or a string tag name.
            attr: Optional attributes for the new child (only when elem is a string).

        Returns:
            The appended Html element.
        """
        if isinstance(elem, str):
            helem = Html(elem, attr)
        else:
            helem = elem
        self.children.append(helem)
        return helem

    def dump(self):
        """Render this element and all children to an HTML string.

        Returns:
            A complete HTML string for the element tree.
        """
        ret = "<" + self.name
        if self.attr:
            ret += " " + self.attr.replace("'", '"')
        ret += ">"
        for elem in self.children:
            ret += elem.dump()
        if self.value:
            ret += self.value() if callable(self.value) else self.value
        ret += "</" + self.name + ">"
        return ret


def make_start_tag(tag, attrs):
    """Generate an HTML opening tag with attributes.

    Attributes with ``None`` values are rendered as boolean attributes
    (e.g. ``disabled``), while non-None values produce ``key="value"`` pairs.

    Args:
        tag: The HTML tag name.
        attrs: Dictionary of attribute name -> value pairs.

    Returns:
        An HTML opening tag string, e.g. ``<div class="foo" id="bar">``.
    """
    ret = "<" + tag
    for key, value in attrs.items():
        if value is not None:
            ret += ' {}="{}"'.format(key, value)
        else:
            ret += " " + key
    ret += ">"
    return ret


class ITemplate:
    """Template engine for ihtml (indent-based HTML) strings.

    Converts ihtml syntax to standard HTML via :func:`ihtml_to_html_base`,
    then renders using Django's Template engine.
    """

    def __init__(self, ihtml_str):
        """Parse an ihtml template string.

        Replaces bracket-escaped Django template tags (``[% ... %]``)
        with standard ``{% ... %}`` notation before converting to HTML.

        Args:
            ihtml_str: The ihtml source string.
        """
        ihtml_str2 = (
            ihtml_str.replace("[%]", "%")
            .replace("[{", "{{")
            .replace("}]", "}}")
            .replace("[%", "{%")
            .replace("%]", "%}")
        )
        self.html_str = ihtml_to_html_base(None, input_str=ihtml_str2, lang="en")
        self.template = Template(self.html_str)

    def gen(self, argv):
        """Render the template with a given context dictionary.

        Args:
            argv: Context dictionary for Django template rendering.

        Returns:
            The rendered HTML string.
        """
        c = Context(argv)
        return self.template.render(c)
