"""
Indentation and code normalization tools for ihtml/js processing.

Provides utilities for:
- Normalizing indentation in source files
- Converting Python-style indentation to JavaScript formatting
- HTML normalization and indentation
- Multi-line string handling
"""

import io
import logging
from typing import Generator, List, Optional, Tuple

from pytigon_lib.schparser.parser import Parser

logger = logging.getLogger(__name__)


def _convert_strings(lines: io.StringIO) -> Generator[str, None, None]:
    """Convert multi-line triple-quoted strings into single logical lines.

    Processes a stream of lines and joins lines that are part of a multi-line
    triple-quoted string (\"\"\") into a single line joined by newline characters.

    Args:
        lines: A StringIO stream of source code lines.

    Yields:
        Individual lines with multi-line strings collapsed to single lines.
    """
    line_buf = None
    in_string = False
    lines.seek(0)

    for line in lines:
        line = line.rstrip("\n")
        idx = line.find('"""')

        if in_string:
            if idx >= 0:
                # End of multi-line string found
                yield f"{line_buf}\n{line}" if line_buf else line
                line_buf = None
                in_string = False
            else:
                # Continue accumulating multi-line string
                line_buf = f"{line_buf}\n{line}" if line_buf else line
        else:
            if idx >= 0:
                # Check if the string closes on the same line
                second_idx = line[idx + 3 :].find('"""')
                if second_idx >= 0:
                    # Single-line triple-quoted string - no change needed
                    yield f"{line_buf}\n{line}" if line_buf else line
                    line_buf = None
                else:
                    # Start of multi-line string
                    in_string = True
                    line_buf = f"{line_buf}\n{line}" if line_buf else line
            else:
                yield line
                line_buf = None


def count_leading_spaces(s: str) -> int:
    """Count the number of leading space characters in a string.

    Args:
        s: Input string.

    Returns:
        Number of leading space characters.
    """
    return len(s) - len(s.lstrip(" "))


def norm_tab(file_stream: io.StringIO) -> List[Tuple[int, str]]:
    """Normalize indentation levels in source code.

    Reads a stream of code, detects indentation changes, and produces
    a normalized list of (indent_level, code_line) tuples.

    Args:
        file_stream: A StringIO stream of source code.

    Returns:
        List of (indent_level, code_line) tuples with normalized levels.
    """
    old_indent = 0
    current_level = 0
    indent_stack = [0]
    result = []

    for line in _convert_strings(file_stream):
        line = line.replace("\t", " " * 8).rstrip()
        if not line.strip():
            continue

        indent = count_leading_spaces(line)

        if indent > old_indent:
            current_level += 1
            indent_stack.append(indent)
        elif indent < old_indent:
            while indent < indent_stack[-1]:
                current_level -= 1
                indent_stack.pop()

        stripped = line[indent:]
        if stripped:
            result.append((current_level, stripped))

        old_indent = indent

    return result


def reformat_js(tab_code: List[Tuple[int, str]]) -> List[List]:
    """Reformat Python-style indented code to JavaScript syntax.

    Converts indentation-based block structure into brace-delimited
    JavaScript blocks with proper separators.

    Args:
        tab_code: List of (indent_level, code) tuples from norm_tab().

    Returns:
        List of [indent_level, code_with_braces] lists.
    """
    tab_code2 = []

    for level, code in tab_code:
        postfix = ""
        sep = ""

        # Handle Python-to-JS syntax transformations
        if code.startswith("def ") and code.endswith(":"):
            code = "function " + code[4:]
        elif code.endswith("({"):
            postfix = "})"
            code = code[:-2] + "({"
            sep = ","
        elif code.endswith("("):
            postfix = ")"
            code = code[:-1] + "("
            sep = ","
        elif code.endswith("["):
            postfix = "]"
            code = code[:-1] + "["
            sep = ","
        elif code.endswith("[,"):
            postfix = "],"
            code = code[:-2] + "["
            sep = ","
        elif code.endswith(":"):
            postfix = "}"
            code = code[:-1] + "{"
            sep = ";"
        elif code.endswith("/:"):
            postfix = ""
            sep = ""
            code = code[:-2]
        elif code.endswith("="):
            postfix = "}"
            code = code[:-1] + "= {"
            sep = ","
        elif code.endswith("{"):
            postfix = "}"
            code = code[:-1] + "{"
            sep = ","

        tab_code2.append((level, code, postfix, sep))

    # Sentinel entry for stack processing
    tab_code2.append((0, "", "", ""))

    tab_code3 = []
    stack = []

    for entry in tab_code2:
        level, code, postfix, sep = entry

        # Pop stack entries that are at same or higher level
        while stack:
            if level > stack[-1][0]:
                stack.append(entry)
                break

            top = stack.pop()
            if level == top[0]:
                # Same level: add separator from parent
                if stack:
                    parent_sep = stack[-1][3]
                else:
                    parent_sep = ";"
                tab_code3[-1][1] += parent_sep
            else:
                # Lower level: add closing postfix
                if stack:
                    tab_code3.append([stack[-1][0], stack[-1][2]])

        tab_code3.append([level, code])

        if not stack:
            stack.append(entry)

    return tab_code3


def file_norm_tab(
    file_in: Optional[io.StringIO], file_out: Optional[io.StringIO]
) -> bool:
    """Normalize indentation in a file and write the result.

    Args:
        file_in: Input StringIO stream to normalize.
        file_out: Output StringIO stream for normalized content.

    Returns:
        True if successful, False if either stream is None.
    """
    if file_in and file_out:
        try:
            tab_code = norm_tab(file_in)
            for level, code in tab_code:
                file_out.write(f"{' ' * 4 * level}{code}\n")
            return True
        except Exception:
            logger.exception("Error normalizing file indentation")
            return False
    return False


def convert_js(
    stream_in: Optional[io.StringIO], stream_out: Optional[io.StringIO]
) -> bool:
    """Convert Python-indented code to JavaScript syntax.

    Normalizes indentation, reformats to JS syntax, and writes output.

    Args:
        stream_in: Input StringIO stream with Python-style indented code.
        stream_out: Output StringIO stream for JavaScript output.

    Returns:
        True if successful, False if either stream is None or on error.
    """
    if stream_in and stream_out:
        try:
            tab_code = norm_tab(stream_in)
            tab_code = reformat_js(tab_code)
            for level, code in tab_code:
                cleaned = code.replace("};", "}").replace(";;", ";")
                stream_out.write(f"{' ' * 4 * level}{cleaned}\n")
            return True
        except Exception:
            logger.exception("Error converting to JavaScript")
            return False
    return False


class NormParser(Parser):
    """HTML parser that normalizes HTML to a compact indented format.

    Uses triple-comma (,,,) as attribute separator and triple-dot (...)
    as content prefix in the output format.
    """

    def __init__(self) -> None:
        """Initialize the normalizing parser."""
        super().__init__()
        self.txt = io.StringIO()
        self.tab = 0

    def _remove_spaces(self, value: str) -> str:
        """Strip leading and trailing whitespace from a string.

        Args:
            value: String to clean.

        Returns:
            Stripped string.
        """
        return value.strip()

    def _print_attr(self, attr: dict) -> str:
        """Format HTML attributes for output.

        Args:
            attr: Dictionary of attribute name-value pairs.

        Returns:
            Formatted attribute string using ,,, as separator.
        """
        return ",,,".join(f"{k}={v}" if v else k for k, v in attr)

    def handle_starttag(self, tag: str, attrs: dict) -> None:
        """Process an opening HTML tag.

        Args:
            tag: HTML tag name.
            attrs: Dictionary of tag attributes.
        """
        self.txt.write(f"\n{' ' * self.tab * 4}{tag} {self._print_attr(attrs)}")
        self.tab += 1

    def handle_endtag(self, tag: str) -> None:
        """Process a closing HTML tag.

        Args:
            tag: HTML tag name.
        """
        self.tab -= 1

    def handle_startendtag(self, tag: str, attrs: dict) -> None:
        """Process a self-closing HTML tag.

        Args:
            tag: HTML tag name.
            attrs: Dictionary of tag attributes.
        """
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data: str) -> None:
        """Process text content within an HTML element.

        Args:
            data: Text content to process.
        """
        if self._remove_spaces(data):
            self.txt.write(f"...{self._remove_spaces(data).replace('\n', '\\n')}")

    def process(self, data: str) -> str:
        """Parse HTML data and return normalized output.

        Args:
            data: Raw HTML string to parse.

        Returns:
            Normalized HTML string in indented format.
        """
        self.feed(data)
        return self.txt.getvalue()


class IndentHtmlParser(NormParser):
    """HTML parser that produces properly indented HTML output."""

    def handle_starttag(self, tag: str, attrs: dict) -> None:
        """Process an opening HTML tag with indentation.

        Args:
            tag: HTML tag name.
            attrs: Dictionary of tag attributes.
        """
        self.txt.write(f"\n{' ' * self.tab * 4}{self.get_starttag_text()}")
        self.tab += 1

    def handle_endtag(self, tag: str) -> None:
        """Process a closing HTML tag with indentation.

        Args:
            tag: HTML tag name.
        """
        self.tab = max(self.tab - 1, 0)
        self.txt.write(f"\n{' ' * self.tab * 4}</{tag}>")

    def handle_data(self, data: str) -> None:
        """Process text content with indentation.

        Args:
            data: Text content to process.
        """
        if data.strip():
            self.txt.write(f"\n{' ' * self.tab * 4}{data.strip()}")


def norm_html(txt: str) -> str:
    """Normalize HTML content to compact indented format.

    Args:
        txt: Raw HTML string.

    Returns:
        Normalized HTML in indented format.
    """
    parser = NormParser()
    return parser.process(txt)


def indent_html(txt: str) -> str:
    """Re-indent HTML content with proper nesting.

    Args:
        txt: Raw HTML or normalized HTML string.

    Returns:
        Properly indented HTML string. Returns original text on error.
    """
    try:
        parser = IndentHtmlParser()
        ret = parser.process(txt)
        lines = [line for line in ret.split("\n") if line.strip()]
        return "\n".join(lines)
    except Exception:
        logger.exception("Error indenting HTML")
        return txt


if __name__ == "__main__":
    import os

    test_dir = os.path.join(os.path.dirname(__file__), "test")

    # Example: normalize HTML to ihtml format
    if False:
        input_path = os.path.join(test_dir, "test11.html")
        output_path = os.path.join(test_dir, "test11.ihtml")
        with open(input_path, "r") as f_in, open(output_path, "w") as f_out:
            ret = norm_html(f_in.read())
            f_out.write(ret)

    # Example: convert ihtml back to formatted HTML
    if True:
        input_path = os.path.join(test_dir, "test11.ihtml")
        output_path = os.path.join(test_dir, "_test11.html")
        with open(input_path, "r") as f_in, open(output_path, "w") as f_out:
            ret = indent_html(f_in.read())
            f_out.write(ret)
