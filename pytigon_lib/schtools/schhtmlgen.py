import collections
from django.template import Template, Context
from pytigon_lib.schindent.indent_style import ihtml_to_html_base


class Html:
    """Represents an HTML element with attributes and children."""

    def __init__(self, name, attr=None):
        """Initialize the HTML element with a name and optional attributes."""
        self.name = name
        self.attr = attr
        self.value = None
        self.children = []

    def setvalue(self, value):
        """Set the value of the HTML element."""
        self.value = value

    def setattr(self, attr):
        """Set the attributes of the HTML element."""
        self.attr = attr

    def append(self, elem, attr=None):
        """Append a child element to the HTML element."""
        if isinstance(elem, str):
            helem = Html(elem, attr)
        else:
            helem = elem
        self.children.append(helem)
        return helem

    def dump(self):
        """Generate the HTML string representation of the element and its children."""
        ret = f"<{self.name}"
        if self.attr:
            ret += f" {self.attr.replace("'", '"')}"
        ret += ">"
        for elem in self.children:
            ret += elem.dump()
        if self.value:
            ret += self.value() if callable(self.value) else self.value
        ret += f"</{self.name}>"
        return ret


def make_start_tag(tag, attrs):
    """Generate an HTML start tag with attributes."""
    ret = f"<{tag}"
    for key, value in attrs.items():
        if value is not None:
            ret += f' {key}="{value}"'
        else:
            ret += f" {key}"
    ret += ">"
    return ret


class ITemplate:
    """Template class for generating HTML from ihtml strings."""

    def __init__(self, ihtml_str):
        """Initialize the template with an ihtml string."""
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
        """Generate the final HTML by rendering the template with the given context."""
        c = Context(argv)
        return self.template.render(c)
