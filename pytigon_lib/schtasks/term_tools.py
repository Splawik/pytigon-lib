import re
from io import StringIO

# Regular expression to match ANSI escape codes
ansi_pattern = r"\033\[((?:\d|;)*)([a-zA-Z])"
ansi_eng = re.compile(ansi_pattern)

# Predefined colors for ANSI codes
COLORS = ("000", "f00", "0f0", "ff0", "00f", "f0f", "0ff", "fff")


def convert_m(code):
    """
    Convert ANSI 'm' codes to HTML tags.

    Args:
        code (str): The ANSI code to convert.

    Returns:
        tuple: A tuple containing the start and end HTML tags.
    """
    if code == "0":
        return (None, None)

    start = ""
    end = ""
    codes = code.split(";")

    for c in codes:
        try:
            cc = int(c)
            if cc == 1:
                start += "<strong>"
                end = "</strong>" + end
            elif 30 <= cc <= 37:
                start += f"<span color='#{COLORS[cc - 30]}'>"
                end = "</span>" + end
        except ValueError:
            continue  # Skip invalid codes

    return (start, end)


def convert_ansi_codes(code):
    """
    Convert ANSI codes to HTML tags based on the code type.

    Args:
        code (str): The ANSI code to convert.

    Returns:
        tuple: A tuple containing the start and end HTML tags.
    """
    if code and code[-1] == "m":
        return convert_m(code[:-1])
    return ("", "")


def ansi_to_txt(ansi_txt):
    """
    Convert ANSI formatted text to plain text with HTML tags.

    Args:
        ansi_txt (str): The ANSI formatted text.

    Returns:
        str: The converted text with HTML tags.
    """
    last = 0
    output = StringIO()
    stack = ""
    txt = ansi_txt.replace("\n", "").replace("\r", "")

    for match in ansi_eng.finditer(txt):
        start, end = match.span()
        output.write(txt[last:start])

        code = "".join(match.groups())
        start_tag, end_tag = convert_ansi_codes(code)

        if start_tag is None:
            output.write(stack)
            stack = ""
        else:
            output.write(start_tag)
            stack += end_tag

        last = end

    output.write(txt[last:])
    if stack:
        output.write(stack)

    return output.getvalue()
