from django import forms
from pytigon_lib.schdjangoext import fields as ext_fields

FAST_FORM_EXAMPLE = """#Example

#Syntax 1 - string format:

What is this?
Name
Second name::*
name//Name!::*
Description::_
Date::####.##.##
Quantity::0
Amount!::9.99
Choose::[option1;option2
option3]
Age::000
Code::****

#Syntax 2 - code:
from django import forms
    
def make_form_class(base_form, init_data):
    class form_class(base_form):
        class Meta(base_form.Meta):
            widgets = {
                "description": form_fields.Textarea(attrs={"cols": 80, "rows": 3}),
            }
    additional_field1 = forms.ImageField(label='label 1', required=False, widget=ImgFileInput)
    additional_field2 = forms.BooleanField(label='label 2, required=False)

    return form_class
"""


def _scan_lines(input_str):
    """Scan input string and split into lines, handling multi-line choices."""
    lines = input_str.replace("\r", "").split("\n")
    result = []
    append_to_last = False

    for line in lines:
        if append_to_last:
            result[-1] = result[-1] + ";" + line
            if "]" in line:
                append_to_last = False
        else:
            result.append(line)
            if ":[" in line and "]" not in line:
                append_to_last = True
    return result


def _get_name_and_title(s):
    """Extract name, title, and required flag from a string."""
    required = s.endswith("!")
    s = s[:-1] if required else s

    if "//" in s:
        name, title = s.split("//", 1)
    else:
        title = s
        name = "".join(
            z
            for z in s.encode("ascii", "replace")
            .decode("utf-8")
            .replace("?", "_")
            .lower()
            if z.isalnum() or z == "_"
        )[:16]
    return name, title, required


def _read_form_line(line):
    """Parse a single line to extract field information."""
    kwargs = {}
    field_type = None
    title = ""
    name = ""
    required = False
    format_str = ""

    if "::" in line:
        line_parts = line.rsplit("::", 1)
        line2 = line_parts[0].strip()
        format_str = line_parts[1].strip()

        if format_str.startswith("0"):
            field_type = forms.IntegerField
            if len(format_str) > 1:
                kwargs = {"min_value": 0, "max_value": 10 ** len(format_str)}
        elif format_str.startswith("9"):
            field_type = forms.FloatField
            if len(format_str) > 1:
                kwargs = {"min_value": 0, "max_value": 10 ** len(format_str)}
        elif format_str.startswith("#"):
            field_type = forms.DateField
        elif format_str.startswith("*"):
            field_type = forms.CharField
            kwargs = {"max_length": len(format_str)}
        elif format_str.startswith("_"):
            field_type = forms.CharField
            kwargs = {"widget": forms.Textarea}
        elif format_str.startswith("["):
            field_type = forms.ChoiceField
            choices = [
                (choice, choice)
                for choice in format_str[1:-1].replace(",", ";").split(";")
                if choice
            ]
            kwargs = {"choices": choices}
    else:
        if line.endswith("?"):
            field_type = forms.BooleanField
            line2 = line[:-1].strip()
        else:
            field_type = forms.CharField
            line2 = line

    name, title, required = _get_name_and_title(line2)
    return name, field_type, title, required, kwargs


def form_from_str(input_str, init_data=None, base_form_class=forms.Form, prefix=""):
    """Generate a Django form from a string definition."""
    if init_data is None:
        init_data = {}

    if "make_form_class" in input_str:
        locals_dict = {}
        exec(input_str, globals(), locals_dict)
        return locals_dict["make_form_class"](base_form_class, init_data)

    class _Form(base_form_class):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            lines = _scan_lines(input_str)

            for line in lines:
                if line:
                    name, field_type, title, required, form_kwargs = _read_form_line(
                        line.strip()
                    )
                    field_name = prefix + name
                    if name in init_data:
                        self.fields[field_name] = field_type(
                            label=title,
                            required=required,
                            initial=init_data[name],
                            **form_kwargs,
                        )
                    else:
                        self.fields[field_name] = field_type(
                            label=title, required=required, **form_kwargs
                        )

    return _Form
