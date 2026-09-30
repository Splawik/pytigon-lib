"""ihtml to HTML conversion utilities for Django templates.

Provides the bridge between the ihtml (indentation-based HTML shorthand)
format and standard HTML. Used by the template loaders to compile
.ihtml source files into .html templates.
"""

import logging

from django.template import TemplateSyntaxError

from pytigon_lib.schindent.indent_style import ConwertToHtml

LOGGER = logging.getLogger("pytigon.schdjangoext")

# Elements that should be self-closing in HTML
SIMPLE_CLOSE_ELEM = ("br", "meta", "input")

# Django template elements that should auto-close.
# ``ifequal``/``ifnotequal`` used to live here but were removed in Django 4.0;
# a generated template containing them fails to render with TemplateSyntaxError.
AUTO_CLOSE_DJANGO_ELEM = (
    "for",
    "if",
    "ifchanged",
    "block",
    "filter",
    "with",
)

# Django template elements that should not auto-close
NO_AUTO_CLOSE_DJANGO_ELEM = (
    "else",
    "elif",
)


def fa_icons(value):
    """Generate a Font Awesome ``<i>`` element for the given icon name.

    Args:
        value: Font Awesome icon name (e.g. ``"user"``).

    Returns:
        An HTML string: ``<i class='fa fa-{value}'></i>``.
    """
    return f"<i class='fa fa-{value}'></i>"


def ihtml_to_html(file_name, input_str=None, lang="en"):
    """Convert ihtml syntax to HTML for a given language.

    When ``input_str`` is None the source is read from ``file_name``;
    otherwise ``file_name`` is used as a logical identifier and
    ``input_str`` supplies the content.

    Args:
        file_name: Source file path or logical identifier.
        input_str: Optional inline ihtml content.
        lang: Language code (e.g. ``"en"``, ``"pl"``).

    Returns:
        The rendered HTML string.

    Raises:
        TemplateSyntaxError: If the ihtml source cannot be converted. Raising
            instead of returning an empty string prevents the loader from
            serving a blank page with HTTP 200.
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
            process_new_line=True,
        )
        conwert.process()
        return conwert.to_str()
    except Exception as ex:
        LOGGER.exception("Error during ihtml conversion of '%s'", file_name)
        raise TemplateSyntaxError(
            f"Error during ihtml conversion of '{file_name}': {ex}"
        ) from ex
