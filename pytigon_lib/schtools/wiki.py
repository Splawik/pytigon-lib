"""Helper functions for wiki link formatting and rendering.

Supports ``[[Page Name]]`` wiki syntax with optional modifiers
(``^`` for new window, ``#`` for button style).
"""

from django.conf import settings


def wiki_from_str(wiki_value):
    """Convert a human-readable string into a compact wiki page name.

    Rules:
    - Empty input returns ``"index"``.
    - Strings starting with ``?`` return everything after the second character.
    - Non-ASCII characters are replaced with XML character references,
      then stripped (``&``, ``#``, ``;`` are removed).
    - Words before the first ``-`` are capitalized and truncated to fit
      within 32 characters total.

    Args:
        wiki_value: The human-readable page title.

    Returns:
        A compact wiki identifier (max 32 characters).
    """
    if not wiki_value:
        return "index"

    if wiki_value.startswith("?"):
        return wiki_value[2:]

    # Transliterate non-ASCII characters to XML references, then strip them
    cleaned = (
        wiki_value.encode("ascii", "xmlcharrefreplace")
        .decode("utf-8")
        .replace("&", "")
        .replace("#", "")
        .replace(";", "")
    )

    # Only use the part before the first hyphen as base words
    base = cleaned.split("-")[0].strip()
    words = base.split(" ")
    if not words or words == [""]:
        return "index"

    word_size = max(1, 32 // len(words))

    formatted = []
    for word in words:
        if len(word) > 1:
            formatted.append(word[0].upper() + word[1:word_size])
        else:
            formatted.append(word.upper())

    wiki = "".join(formatted)[:32]
    return wiki if wiki else "index"


def make_href(wiki_value, new_win=True, section=None, btn=False, path=None):
    """Generate an HTML anchor tag for a wiki link.

    Args:
        wiki_value: The wiki page title.
        new_win: If True, link opens in ``_top2`` target.
        section: Optional wiki section name for generating the URL.
        btn: If True, style the link as a Bootstrap button.
        path: Optional path prefix (joined with ``+``).

    Returns:
        An HTML ``<a>`` tag string.
    """
    wiki = wiki_from_str(wiki_value)
    if path:
        wiki = f"{path}+{wiki}"

    url_root = f"/{settings.URL_ROOT_FOLDER}" if settings.URL_ROOT_FOLDER else ""
    btn_class = "btn btn-secondary" if btn else "schbtn"
    btn_str = f"class='{btn_class}' label='{wiki_value}'"

    if section:
        href = f"{url_root}/schwiki/{section}/{wiki}/view/?desc={wiki_value}"
    else:
        href = f"../../{wiki}/view/?desc={wiki_value}"

    target = "_top2" if new_win else "_self"
    return f"<a href='{href}' target='{target}' {btn_str}>{wiki_value}</a>"


def wikify(value, path=None, section=None):
    """Replace ``[[...]]`` wiki markup in a string with HTML links.

    Supports modifiers:
    - ``[[^Page]]`` — opens in new window.
    - ``[[#Page]]`` — styled as a button.
    - ``[[Page;section]]`` — overrides the section for this link.

    Args:
        value: The string containing wiki markup.
        path: Optional path prefix for all links.
        section: Default wiki section for all links.

    Returns:
        The string with ``[[...]]`` replaced by HTML ``<a>`` tags.
    """
    if not value:
        return value

    parts = value.split("[[")
    if len(parts) == 1:
        return value

    result = [parts[0]]
    for part in parts[1:]:
        subparts = part.split("]]")
        if len(subparts) == 2 and subparts[0]:
            txt = subparts[0]
            new_win = txt.startswith("^")
            btn = txt.startswith("#")
            if new_win or btn:
                txt = txt[1:]

            if ";" in txt:
                txt, _section = txt.split(";", 1)
            else:
                _section = section

            result.append(
                make_href(txt, new_win=new_win, section=_section, btn=btn, path=path)
                + subparts[1]
            )
        else:
            result.append("[[%s" % part)

    return "".join(result)
