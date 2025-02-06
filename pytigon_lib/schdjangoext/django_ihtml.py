from pytigon_lib.schindent.indent_style import ConwertToHtml

# Elements that should be self-closing in HTML
SIMPLE_CLOSE_ELEM = ["br", "meta", "input"]

# Django template elements that should auto-close
AUTO_CLOSE_DJANGO_ELEM = [
    "for",
    "if",
    "ifequal",
    "ifnotequal",
    "ifchanged",
    "block",
    "filter",
    "with",
]

# Django template elements that should not auto-close
NO_AUTO_CLOSE_DJANGO_ELEM = [
    "else",
    "elif",
]


def fa_icons(value):
    """Generate Font Awesome icon HTML.

    Args:
        value (str): The name of the Font Awesome icon.

    Returns:
        str: HTML string for the icon.
    """
    return f"<i class='fa fa-{value}'></i>"


def ihtml_to_html(file_name, input_str=None, lang="en"):
    """Convert ihtml syntax to HTML.

    Args:
        file_name (str): The name of the template file.
        input_str (str, optional): The input string with ihtml content. Defaults to None.
        lang (str, optional): The language. Defaults to "en".

    Returns:
        str: The converted HTML string or an empty string on error.
    """
    try:
        conwert = ConwertToHtml(
            file_name,
            SIMPLE_CLOSE_ELEM,
            AUTO_CLOSE_DJANGO_ELEM,
            NO_AUTO_CLOSE_DJANGO_ELEM,
            input_str,
            lang,
            output_processors={
                "fa": fa_icons,
            },
        )
        conwert.process()
        return conwert.to_str()
    except Exception as e:
        print(f"Error during ihtml conversion: {e}")
        import traceback
        import sys

        print(sys.exc_info()[0])
        print(traceback.print_exc())

        return ""
