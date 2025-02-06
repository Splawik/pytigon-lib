"""Module contains helper functions to handle wiki links and formatting."""

from django.conf import settings


def wiki_from_str(wiki_value):
    """Convert a string into a wiki-friendly format.

    Args:
        wiki_value (str): The string to be converted.

    Returns:
        str: A wiki-friendly string.
    """
    if not wiki_value:
        return "index"

    if wiki_value.startswith("?"):
        return wiki_value[2:]

    # Clean the string by removing unwanted characters
    cleaned_value = (
        wiki_value.encode("ascii", "xmlcharrefreplace")
        .decode("utf-8")
        .replace("&", "")
        .replace("#", "")
        .replace(";", "")
    )

    # Split the cleaned string into words
    words = cleaned_value.split("-")[0].strip().split(" ")
    word_size = max(1, 32 // len(words))  # Ensure word_size is at least 1

    # Capitalize and truncate each word
    formatted_words = [
        word[0].upper() + word[1:word_size] if len(word) > 1 else word.upper()
        for word in words
    ]

    # Join the words and truncate to 32 characters
    wiki = "".join(formatted_words)[:32]
    return wiki if wiki else "index"


def make_href(wiki_value, new_win=True, section=None, btn=False, path=None):
    """Generate an HTML link for a wiki entry.

    Args:
        wiki_value (str): The wiki entry to link to.
        new_win (bool): Whether to open the link in a new window.
        section (str): The section of the wiki to link to.
        btn (bool): Whether to style the link as a button.
        path (str): Additional path to prepend to the wiki link.

    Returns:
        str: An HTML anchor tag.
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
    """Convert a string containing wiki links into HTML.

    Args:
        value (str): The string to be wikified.
        path (str): Additional path to prepend to wiki links.
        section (str): The section of the wiki to link to.

    Returns:
        str: The wikified string with HTML links.
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
            txt = txt[1:] if new_win or btn else txt

            if ";" in txt:
                txt, _section = txt.split(";", 1)
            else:
                _section = section

            result.append(
                make_href(txt, new_win=new_win, section=_section, btn=btn, path=path)
                + subparts[1]
            )
        else:
            result.append(f"[[{part}")

    return "".join(result)
