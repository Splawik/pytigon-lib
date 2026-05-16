"""
IHTML to HTML style converter.

Converts indented ihtml source files into standard HTML with support for:
- Django template tags (% prefix)
- Python-to-JavaScript compilation (>>> marker, {:} marker, pscript)
- Markdown conversion (###> marker)
- Translation and table formatting
- Inline content optimization

The ihtml format uses indentation to indicate nesting (like Python/HAML).
"""

import codecs
import gettext
import io
import logging
import os
import os.path
from collections.abc import Callable, Generator
from typing import Any, Dict, List, Optional, TextIO, Tuple, Union

from django.conf import settings

from pytigon_lib.schindent.indent_tools import convert_js
from pytigon_lib.schindent.py_to_js import compile as py_to_js_compile
from pytigon_lib.schtools.main_paths import get_prj_name
from pytigon_lib.schtools.tools import norm_indent

logger = logging.getLogger(__name__)

# ---- Markdown support (optional) ----

_convert_md = None

try:
    import markdown

    def _convert_md(stream_in: io.StringIO, stream_out: io.StringIO) -> bool:
        """Convert Markdown content to HTML and write to output stream.

        Args:
            stream_in: Input StringIO containing Markdown content.
            stream_out: Output StringIO for HTML output.

        Returns:
            True if conversion succeeded, False if streams are None.
        """
        if stream_in and stream_out:
            buf = markdown.markdown(
                norm_indent(stream_in.getvalue()),
                extensions=[
                    "abbr",
                    "attr_list",
                    "def_list",
                    "fenced_code",
                    "footnotes",
                    "md_in_html",
                    "tables",
                    "admonition",
                    "codehilite",
                ],
            )
            stream_out.write(buf)
            return True
        return False

except Exception:
    logger.debug("Markdown library not available; markdown conversion disabled")


# ---- Utility functions ----


def list_with_next_generator(
    items: List[Any],
) -> Generator[Tuple[Any, Optional[Any]], None, None]:
    """Yield each item paired with its successor (or None for the last).

    Args:
        items: Non-empty list of items.

    Returns:
        Generator yielding (current, next) tuples.
    """
    if not items:
        return
    current = items[0]
    for item in items[1:]:
        yield (current, item)
        current = item
    yield (items[-1], None)


def translate(s: str) -> str:
    """Identity translation function (no-op).

    Args:
        s: String to translate.

    Returns:
        Original string unchanged.
    """
    return s


def _build_translator(lang: str) -> Tuple[Callable[[str], str], List[str]]:
    """Build a gettext-based translator function for the given language.

    Also collects translatable strings into a list for later export.

    Args:
        lang: Language code (e.g., 'pl', 'de'). 'en' uses identity.

    Returns:
        Tuple of (translate_function, collected_words_list).
    """
    if lang == "en":
        return translate, []

    base_path = os.path.join(settings.PRJ_PATH, get_prj_name())
    locale_path = os.path.join(base_path, "locale")
    collected_words: List[str] = []

    # Try to load gettext translation
    try:
        t = gettext.translation("django", locale_path, languages=[lang])
        t.install()
    except Exception:
        t = None

    # Try to load existing translations from translate.py
    try:
        translate_path = os.path.join(base_path, "translate.py")
        with open(translate_path, encoding="utf-8") as f:
            for line in f:
                parts = line.split('_("')
                if len(parts) > 1:
                    parts = parts[1].split('")')
                    if len(parts) == 2:
                        collected_words.append(parts[0])
    except Exception:
        pass

    def trans(word: str) -> str:
        """Translate a word, handling quoted strings."""
        if len(word) < 2:
            return word

        # Detect surrounding quotes
        if (word[0] == word[-1] == '"') or (word[0] == word[-1] == "'"):
            quote_char = word[0]
            word2 = word[1:-1]
            strtest = quote_char
        else:
            strtest = None
            word2 = word

        if word2 not in collected_words:
            collected_words.append(word2)

        if t:
            ret = t.gettext(word2)
            if strtest is not None:
                return strtest + ret + strtest
            return ret
        return translate(word)

    return trans, collected_words


def iter_lines(
    file_stream: Union[TextIO, io.StringIO], file_name: Optional[str], lang: str
) -> Generator[str, None, None]:
    """Iterate over lines from a file, applying translation and table formatting.

    Handles:
    - Translation of _() prefixed lines
    - Table syntax ([...|...]) conversion to <tr><td> format

    Args:
        file_stream: Input file or StringIO to read from.
        file_name: Original file name (for saving translations).
        lang: Language code for translation.

    Yields:
        Processed lines, with a final '.' sentinel.
    """
    translator_fn, collected_words = _build_translator(lang)
    in_table = 0

    for line in file_stream:
        stripped = line.lstrip()

        # Handle translation prefix _
        if stripped.startswith("_") and not stripped.startswith("_("):
            nr = line.find("_")
            line2 = " " * nr + "." + translator_fn(line.strip()[1:])
        elif "_(" in line and "__(" not in line:
            # Handle inline _("text") patterns
            out = []
            if stripped.startswith("_("):
                fr0 = line.split("_(")
                fr = (fr0[0] + ".", fr0[1])
            else:
                fr = line.split("_(")
            out.append(fr[0])
            for pos in fr[1:]:
                id2 = pos.find(")")
                if id2 >= 0:
                    out.append(translator_fn(pos[:id2]))
                    out.append(pos[id2 + 1 :])
                else:
                    out.append(translator_fn(pos))
            line2 = "".join(out)
        else:
            line2 = line

        # Table syntax detection and conversion
        line3 = line2.strip()
        if line3 and (line3[0] == "[" or line3[-1] == "]" or "|" in line3):
            if line3[0] == "[" and (
                line3[-1] == "|" or (line3[-1] == "]" and "|" in line3)
            ):
                in_table = 2 if line3[1] == "[" else 1

            if in_table == 1:
                line2 = (
                    line2.replace("[", "<tr><td>")
                    .replace("]", "</td></tr>")
                    .replace(" |", " </td><td>")
                )
            elif in_table == 2:
                line2 = (
                    line2.replace("[[", "<tr><th>")
                    .replace("]]", "</th></tr>")
                    .replace(" |", " </th><th>")
                )

            if line3[-1] == "]":
                in_table = 0

        yield line2

    yield "."

    # Save collected translation words to file
    if collected_words:
        base_path = os.path.join(settings.PRJ_PATH, get_prj_name())
        if "site-packages" not in base_path:
            try:
                translate_path = os.path.join(base_path, "translate.py")
                with open(translate_path, "w", encoding="utf-8") as f:
                    for word in collected_words:
                        f.write(f'_("{word}")\n')
            except Exception:
                logger.exception("Failed to write translation file")


# ---- Parsing helpers ----


def _space_count(buf: str) -> int:
    """Count leading space characters in a string.

    Args:
        buf: Input string.

    Returns:
        Number of leading space characters.
    """
    i = 0
    for ch in buf:
        if ch == " ":
            i += 1
        else:
            break
    return i


def _get_elem(elem: str) -> str:
    """Extract the tag name from an element string.

    Args:
        elem: Element string, optionally with attributes.

    Returns:
        Tag name (first word before space).
    """
    elem2 = elem.lstrip()
    space_pos = elem2.find(" ")
    if space_pos > 0:
        return elem2[:space_pos]
    return elem2


def _transform_elem(elem: str) -> str:
    """Convert ihtml element syntax to HTML attribute syntax.

    Replaces ,,, separators with proper attribute syntax (key="value").

    Args:
        elem: ihtml element string with ,,, attribute separation.

    Returns:
        HTML element string with standard attribute syntax.
    """
    space_pos = elem.find(" ")
    if space_pos <= 0:
        return elem

    elem_tag = elem[:space_pos]
    elem_attrs = ""

    for attr_part in elem[space_pos + 1 :].split(",,,"):
        eq_pos = attr_part.find("=")
        if eq_pos > 0:
            elem_attrs += f' {attr_part[:eq_pos]}="{attr_part[eq_pos + 1 :]}"'
        else:
            elem_attrs += f" {attr_part}"

    return elem_tag + elem_attrs


def _pre_process_line(line: str) -> List[Optional[Tuple[int, Optional[str], str, int]]]:
    """Pre-process a single ihtml source line into structured components.

    Splits lines at ... separator into code and html parts, handles
    ::: separators for multi-element lines.

    Args:
        line: Raw ihtml source line.

    Returns:
        List of (indent, code, html, status) tuples, or [None] for blank lines.
    """
    n = _space_count(line)
    line2 = line[n:]

    if line2.rstrip() == "":
        return [None]

    first_char = line2[0]

    # Non-element lines (text, comments)
    if not (
        ("a" <= first_char <= "z") or ("A" <= first_char <= "Z") or first_char == "%"
    ):
        if first_char == ".":
            return [(n, None, line2[1:], 0)]
        return [(n, None, line2, 0)]

    # Split code and html parts at ...
    nr = line2.find("...")
    if nr >= 0:
        code = line2[:nr] or None
        html = line2[nr + 3 :]
    else:
        code = line2
        html = None

    if code and code[0] != "%":
        code2 = code.split(":::")
        if len(code2) > 1:
            out = []
            i = n
            for pos in code2[:-1]:
                out.append((i, _transform_elem(pos), None, 3 if i == n else 1))
                i += 1
            out.append((i, _transform_elem(code2[-1]), html, 4))
            return out
        else:
            code = _transform_elem(code)

    return [(n, code, html, 0)]


def _status_close(status: int, line: Tuple, next_line: Tuple) -> int:
    """Calculate the closing status for a line based on current and next line.

    Used in the output formatting to determine line break behavior.

    Args:
        status: Current line status code.
        line: Current line tuple (indent, code, html, status).
        next_line: Next line tuple.

    Returns:
        Adjusted status code.
    """
    if status in (0, 2):
        return 0
    if status == 1:
        return 1
    if status == 3:
        return 2
    if status == 4:
        if next_line[0] > line[0]:
            return 3
        return 1
    return status


# ---- Test mode handling constants ----
TEST_NONE = 0
TEST_RAW = 1  # >>> marker - raw embedded content
TEST_JS = 2  # {:} marker - JS conversion
TEST_PS = 3  # ===> or script language=python
TEST_PY2JS = 4  # script language=py2javascript
TEST_COMPONENT = 5  # %component marker
TEST_MD = 6  # ###> marker - markdown

# Sentinel strings used in ihtml format
MARKER_RAW = ">>>"
MARKER_JS = "{:}"
MARKER_PS = "===>"
MARKER_MD = "###>"


class IhtmlToHtml:
    """Converter from ihtml (indented HTML) format to standard HTML.

    Parses ihtml source files and produces formatted HTML output with
    support for Django template tags, embedded scripts, and inline
    content optimization.

    Attributes:
        file_name: Source file path or None for string input.
        input_str: Input string (used when file_name is None).
        code: Parsed code lines as (indent, element, html, status) tuples.
        buffer: Stack of pending closing tags.
        output: Generated output lines.
        no_convert: If True, pass through without conversion.
        simple_close_tags: Tags that self-close without content.
        auto_close_tags: Tags that auto-close.
        no_auto_close_tags: Tags that should not auto-close even with :.
        lang: Language code for translation.
        output_processors: Optional dict of post-processing functions.
    """

    def __init__(
        self,
        file_name: Optional[str],
        simple_close_tags: List[str],
        auto_close_tags: List[str],
        no_auto_close_tags: List[str],
        input_str: Optional[str] = None,
        lang: str = "en",
        output_processors: Optional[Dict[str, Callable]] = None,
    ) -> None:
        """Initialize the converter.

        Args:
            file_name: Path to ihtml file, or None for string input.
            simple_close_tags: Tags that self-close without content (e.g., br, input).
            auto_close_tags: Tags that should auto-close.
            no_auto_close_tags: Tags excluded from auto-closing.
            input_str: Input string (used when file_name is None).
            lang: Language code for gettext translation.
            output_processors: Map of processor name to callable for @@() post-processing.
        """
        self.file_name = file_name
        self.input_str = input_str
        self.code: List[Tuple[int, Optional[str], Optional[str], int]] = []
        self.buffer: List[Tuple[int, str, int]] = []
        self.output: List[Tuple[int, Optional[str], int]] = []
        self.no_convert = False
        self.simple_close_tags = simple_close_tags
        self.auto_close_tags = auto_close_tags
        self.no_auto_close_tags = no_auto_close_tags
        self.lang = lang
        self.output_processors = output_processors

    def _flush_buffer(self, min_indent: int) -> None:
        """Flush buffered closing tags up to the given indentation level.

        Args:
            min_indent: Minimum indentation to flush to.
        """
        for pos in reversed(self.buffer):
            if pos[0] >= min_indent:
                self.output.append([pos[0], pos[1], pos[2]])
                self.buffer.remove(pos)
            else:
                break

    # ---- Line transformation ----

    def transform_line(self, line: Tuple, next_line: Tuple) -> None:
        """Transform a parsed line and its successor into output entries.

        Handles HTML tags, template tags (%), and plain content lines.
        Manages tag opening/closing logic based on indentation changes.

        Args:
            line: Current line tuple (indent, code, html, status).
            next_line: Next line tuple for context.
        """
        if not (line[1] is None and line[2] is None):
            self._flush_buffer(line[0])

        if line[1]:
            if line[1][0] == "%":
                self._transform_template_line(line, next_line)
            else:
                self._transform_html_line(line, next_line)
        else:
            self.output.append([line[0], line[2], line[3]])

    def _transform_template_line(self, line: Tuple, next_line: Tuple) -> None:
        """Handle Django template tag lines (starting with %).

        Args:
            line: Current line tuple.
            next_line: Next line tuple.
        """
        # Double %% = inline block with auto-endblock
        if line[1][1] == "%":
            if next_line[0] <= line[0] and not (
                next_line[1] is None and next_line[2] is None
            ):
                # Next line at same or lower level - wrap as inline block
                tag_content = (line[1])[2:].lstrip()
                self.output.append(
                    [
                        line[0],
                        f"{{% block {tag_content} %}}{line[2] or ''}{{% endblock %}}",
                        line[3],
                    ]
                )
            else:
                # Opening block - close later
                tag_content = (line[1])[2:].lstrip()
                self.output.append(
                    [
                        line[0],
                        f"{{% block {tag_content} %}}",
                        line[3],
                    ]
                )
                if line[2]:
                    self.output.append([line[0], line[2], line[3]])
                self.buffer.append([line[0], "{% endblock %}", line[3]])
        else:
            # Single % = template tag
            auto_end = False
            tag = (line[1])[1:].split()[0].strip()
            full_tag = (line[1])[1:].strip()

            if full_tag.endswith(":"):
                auto_end = True
                tag = tag.replace(":", "")
                full_tag = full_tag[:-1]
                if tag in self.no_auto_close_tags:
                    auto_end = False

            self.output.append([line[0], f"{{% {full_tag} %}}", line[3]])

            if auto_end or tag in self.auto_close_tags or "_ext" in tag:
                self.buffer.append([line[0], f"{{% end{tag} %}}", line[3]])

            if line[2]:
                self.output.append([line[0], line[2], line[3]])

    def _transform_html_line(self, line: Tuple, next_line: Tuple) -> None:
        """Handle HTML element lines.

        Args:
            line: Current line tuple.
            next_line: Next line tuple.
        """
        tag_name = _get_elem(line[1])

        # Check if next line closes this tag
        next_closes = next_line[0] <= line[0] and not (
            next_line[1] is None and next_line[2] is None
        )

        if next_closes:
            if line[2] or tag_name not in self.simple_close_tags:
                # Content-bearing tag - emit with closing tag
                content = line[2] or ""
                self.output.append(
                    [
                        line[0],
                        f"<{line[1]}>{content}</{tag_name}>",
                        _status_close(line[3], line, next_line),
                    ]
                )
            else:
                # Self-closing tag
                self.output.append([line[0], f"<{line[1]} />", line[3]])
        else:
            # Opening tag - defer closing
            self.output.append([line[0], f"<{line[1]}>", line[3]])
            if line[2]:
                self.output.append([line[0], line[2], line[3]])
            self.buffer.append(
                [
                    line[0],
                    f"</{tag_name}>",
                    _status_close(line[3], line, next_line),
                ]
            )

    # ---- Main processing ----

    def transform(self) -> None:
        """Process all parsed lines through the transformation pipeline."""
        old_line = None
        for line in self.code:
            if old_line is None:
                old_line = line
            else:
                self.transform_line(old_line, line)
                old_line = line
        if old_line:
            self.transform_line(old_line, (0, None, None))
        self._flush_buffer(-1)

    def _read_input(self) -> io.StringIO:
        """Open and prepare input stream from file or string.

        Handles @@ referencing for template inclusion.

        Returns:
            StringIO containing the input content.
        """
        if self.file_name:
            with codecs.open(self.file_name, "r", encoding="utf-8") as f:
                first_line = f.readline()
                f.seek(0, 0)

                if first_line.startswith("@@@"):
                    # Template reference: include another file
                    ref_name = first_line[3:].strip()
                    ref_path = (
                        os.path.join(os.path.dirname(self.file_name), ref_name)
                        + ".ihtml"
                    )

                    with codecs.open(ref_path, "r", encoding="utf-8") as f2:
                        content2 = f.read()[len(first_line) :]
                        content = f2.read().replace("@@@", content2)

                    return io.StringIO(content)
                else:
                    return io.StringIO(f.read())
        else:
            return io.StringIO(self.input_str)

    def _pre_process_all_lines(self, file_stream: io.StringIO) -> None:
        """Read, parse, and classify all input lines into self.code.

        Handles special markers for embedded scripts (>>>, {:}, ===>, etc.),
        markdown blocks (###>), and component definitions.

        Args:
            file_stream: Input stream to read from.
        """
        old_pos = 0
        buf: Optional[io.StringIO] = None
        buf0 = ""
        test = TEST_NONE
        cont = False
        indent_pos = 0

        for raw_line in iter_lines(file_stream, self.file_name, self.lang):
            line = (
                raw_line.replace("\n", "").replace("\r", "").replace("\t", "        ")
            )

            # Handle %else in templates
            if line.replace(" ", "") in ("%else", "%else:"):
                line = " " + line

            # Pass-through marker
            if "^^^" in line:
                self.no_convert = True
                file_stream.close()
                return

            if test:
                if (
                    test > TEST_RAW
                    and len(line.strip()) > 0
                    and _space_count(line) <= indent_pos
                ):
                    cont = True

                if cont or MARKER_PS + ">" in line:
                    if test == TEST_RAW:
                        # >>> block - raw content
                        l_clean = (
                            line.replace("\n", "")
                            .replace("\r", "")
                            .replace("\t", "        ")
                            .replace("<<<", "")
                            .rstrip()
                        )
                        buf.write(l_clean)
                        x = _pre_process_line(buf0 + buf.getvalue())
                        for pos in x:
                            if pos:
                                self.code.append((pos[0] * 4, pos[1], pos[2], pos[3]))
                                old_pos = pos[0]
                            else:
                                self.code.append((old_pos * 4, None, None, 1))
                        buf = None
                        test = TEST_NONE
                        continue

                    if test > TEST_RAW:
                        if not cont:
                            l_clean = (
                                line.replace("\n", "")
                                .replace("\r", "")
                                .replace("\t", "        ")
                                .replace("<<<", "")
                                .rstrip()
                            )
                            buf.write(l_clean)

                        if test == TEST_JS:
                            # {:} block - JS conversion
                            buf2 = io.StringIO()
                            convert_js(buf, buf2)
                            x = _pre_process_line(buf0 + buf2.getvalue())

                        elif test == TEST_PS:
                            # pscript block
                            x = _pre_process_line(
                                buf0.replace("pscript", "script language=python")
                                + buf.getvalue()
                            )
                            test = TEST_NONE

                        elif test == TEST_PY2JS:
                            # py2javascript block
                            v = buf.getvalue()
                            codejs = _py_to_js_wrapper(v)
                            x = _pre_process_line(
                                buf0.replace("pscript", "script")
                                .replace(" language=python", "")
                                .replace("py2javascript", "javascript")
                                + codejs
                            )

                        elif test == TEST_COMPONENT:
                            # component block
                            v = buf.getvalue()
                            codejs = _py_to_js_wrapper(v)
                            x = _pre_process_line(
                                buf0.replace("pscript", "script").replace(
                                    " language=python", ""
                                )
                                + codejs
                            )

                        elif test == TEST_MD:
                            # markdown block
                            if _convert_md is not None:
                                buf2 = io.StringIO()
                                _convert_md(buf, buf2)
                                x = _pre_process_line(buf0 + buf2.getvalue())
                            else:
                                x = _pre_process_line(buf0 + buf.getvalue())

                        else:
                            x = _pre_process_line(buf0 + buf.getvalue())

                        for pos in x:
                            if pos:
                                self.code.append((pos[0] * 4, pos[1], pos[2], pos[3]))
                                old_pos = pos[0]
                            else:
                                self.code.append((old_pos * 4, None, None, 1))

                        buf = None
                        buf2 = None
                        test = TEST_NONE
                else:
                    buf.write(
                        line.replace("\n", "")
                        .replace("\r", "")
                        .replace("\t", "        ")
                        .rstrip()
                        + "\n"
                    )
                    continue

            if cont or not test:
                cont = False

                if MARKER_RAW in line:
                    indent_pos = _space_count(line)
                    pos = line.find(MARKER_RAW)
                    prefix = line[: pos + 3]
                    if line[:pos].strip():
                        buf0 = prefix.replace(MARKER_RAW, "...|||")
                    else:
                        buf0 = prefix.replace(MARKER_RAW, ".|||")
                    buf = io.StringIO()
                    buf.write(
                        line[pos + 3 :]
                        .replace("\n", "")
                        .replace("\r", "")
                        .replace("\t", "        ")
                        .rstrip()
                    )
                    test = TEST_RAW

                elif MARKER_JS in line:
                    indent_pos = _space_count(line)
                    pos = line.find(MARKER_JS)
                    prefix = line[: pos + 4]
                    if line[:pos].strip():
                        buf0 = prefix.replace(MARKER_JS, "...|||")
                    else:
                        buf0 = prefix.replace(MARKER_JS, ".|||")
                    buf = io.StringIO()
                    buf.write(
                        line[pos + 4 :]
                        .replace("\n", "")
                        .replace("\r", "")
                        .replace("\t", "        ")
                        .rstrip()
                    )
                    test = TEST_JS

                elif MARKER_PS in line:
                    indent_pos = _space_count(line)
                    pos = line.find(MARKER_PS)
                    prefix = line[: pos + 4]
                    if line[:pos].strip():
                        buf0 = prefix.replace(MARKER_PS, "...|||")
                    else:
                        buf0 = prefix.replace(MARKER_PS, ".|||")
                    buf = io.StringIO()
                    buf.write(
                        line[pos + 4 :]
                        .replace("\n", "")
                        .replace("\r", "")
                        .replace("\t", "        ")
                        .rstrip()
                    )
                    test = TEST_PS

                elif "script language=python" in line:
                    indent_pos = _space_count(line)
                    pos = line.find("script language=python")
                    buf0 = line + "...|||"
                    buf = io.StringIO()
                    buf.write(
                        line[pos + 22 :]
                        .replace("\n", "")
                        .replace("\r", "")
                        .replace("\t", "        ")
                        .rstrip()
                    )
                    test = TEST_PS

                elif "pscript" in line:
                    indent_pos = _space_count(line)
                    buf0 = line + "...|||"
                    buf = io.StringIO()
                    test = TEST_PS

                elif (
                    line.strip().startswith("script")
                    and "language=py2javascript" in line
                ):
                    indent_pos = _space_count(line)
                    buf0 = line + "...|||"
                    buf = io.StringIO()
                    test = TEST_PY2JS

                elif line.strip().replace(" ", "").startswith("%component"):
                    indent_pos = _space_count(line)
                    buf0 = line + "...|||"
                    buf = io.StringIO()
                    test = TEST_COMPONENT

                elif MARKER_MD in line:
                    indent_pos = _space_count(line)
                    pos = line.find(MARKER_MD)
                    prefix = line[: pos + 4]
                    if line[:pos].strip():
                        buf0 = prefix.replace(MARKER_MD, "...|||")
                    else:
                        buf0 = prefix.replace(MARKER_MD, ".|||")
                    buf = io.StringIO()
                    buf.write(
                        line[pos + 4 :]
                        .replace("\n", "")
                        .replace("\r", "")
                        .replace("\t", "        ")
                        .rstrip()
                    )
                    test = TEST_MD

                else:
                    # Regular line
                    l_clean = (
                        line.replace("\n", "")
                        .replace("\r", "")
                        .replace("\t", "        ")
                        .rstrip()
                    )
                    x = _pre_process_line(l_clean)
                    for pos in x:
                        if pos:
                            self.code.append((pos[0] * 4, pos[1], pos[2], pos[3]))
                            old_pos = pos[0]
                        else:
                            self.code.append((old_pos * 4, None, None, 1))

        file_stream.close()
        self.code.append((0, None, None, 1))
        self.transform()

    def process(self) -> None:
        """Run the full conversion pipeline on the input."""
        file_stream = self._read_input()
        self._pre_process_all_lines(file_stream)

    # ---- Output formatting ----

    def to_str(self, beauty: bool = True) -> str:
        """Generate the final HTML string from processed output.

        Args:
            beauty: If True, produce nicely formatted output with line breaks
                    and indentation. If False, produce more compact output.

        Returns:
            Final HTML string.
        """
        if self.no_convert:
            return self._no_convert_output()

        output = ""

        if beauty:
            output = self._format_beautiful(output)
        else:
            output = self._format_compact(output)

        # Process @@() inline processors
        if self.output_processors and "@@(" in output:
            output = self._apply_output_processors(output)

        output = output.replace("\r", "").replace("\\\n", "")

        # Handle <inline:> optimization
        if "<inline:>" in output:
            output = self._optimize_inline(output)

        return output

    def _no_convert_output(self) -> str:
        """Return raw input when no_convert is set."""
        if self.file_name:
            with codecs.open(self.file_name, "r", encoding="utf-8") as f:
                output = f.read().replace("^^^", "")
        else:
            output = self.input_str.replace("^^^", "")
        return output.replace("\r", "").replace("\\\n", "")

    def _format_beautiful(self, output: str) -> str:
        """Format output with proper indentation and line breaks.

        Args:
            output: Accumulated output string.

        Returns:
            Beautifully formatted output.
        """
        if not self.output:
            return ""

        for line, nextline in list_with_next_generator(self.output):
            # Add indentation for status 0 and 3
            if line[0] >= 0 and line[2] in (0, 3):
                output += " " * int(line[0] / 2)
            if line[1]:
                output += line[1]
            # Line break for status 0 and 2
            if line[2] in (0, 2):
                output += "\n"
            # Line break for status 4 when next is deeper
            if line[2] == 4 and nextline and nextline[0] > line[0]:
                output += "\n"

        return output.replace("|||", "\n")

    def _format_compact(self, output: str) -> str:
        """Format output with minimal line breaks.

        Args:
            output: Accumulated output string.

        Returns:
            Compactly formatted output.
        """
        if not self.output:
            return ""

        for line, nextline in list_with_next_generator(self.output):
            # Indentation only for status 3
            if line[0] >= 0 and line[2] == 3:
                output += " " * int(line[0] / 2)
            if line[1]:
                output += line[1]
            # Line break for status 2
            if line[2] == 2 or (line[2] == 4 and nextline and nextline[0] > line[0]) or (
                line[1]
                and nextline
                and nextline[1]
                and not (
                    line[1].strip().startswith("<") or line[1].strip().startswith("{")
                )
                and not (
                    nextline[1].strip().startswith("<")
                    or nextline[1].strip().startswith("{")
                )
            ):
                output += "\n"

        return output.replace("|||", "\n")

    def _apply_output_processors(self, output: str) -> str:
        """Apply registered post-processors to @@() blocks.

        Args:
            output: Output string with @@() markers.

        Returns:
            Processed output string.
        """
        tab_tmp1 = output.split("@@(")
        ret2 = []

        for pos in tab_tmp1:
            if ret2:
                tab_tmp2 = pos.split(")", 1)
                if len(tab_tmp2) > 1:
                    value = tab_tmp2[0]
                    if "://" in value:
                        fun, value = value.split("://", 1)
                    elif "-" in value:
                        fun, value = value.split("-", 1)
                    else:
                        fun = "default"
                    if fun in self.output_processors:
                        ret2.append(self.output_processors[fun](value))
                    ret2.append(tab_tmp2[1])
                else:
                    ret2.append(pos)
            else:
                ret2.append(pos)

        return "".join(ret2)

    @staticmethod
    def _optimize_inline(output: str) -> str:
        """Optimize <inline:> blocks by joining lines within them.

        Args:
            output: Output string with <inline:> tags.

        Returns:
            Output with inline content collapsed to single lines.
        """
        # Normalize whitespace around inline tags
        prev_len = len(output)
        while True:
            output = (
                output.replace(" <inline:>", "<inline:>")
                .replace("\n<inline:>", "<inline:>")
                .replace("</inline:> ", "</inline:>")
                .replace("</inline:>\n", "</inline:>")
            )
            if len(output) == prev_len:
                break
            prev_len = len(output)

        parts = output.split("<inline:>")
        result = [parts[0]]

        for item in parts[1:]:
            sub_parts = item.split("</inline:>")
            lines = sub_parts[0].split("\n")
            s = " ".join(ln.replace("\r", "").strip() for ln in lines)
            s = (
                s.replace("> ", ">")
                .replace("} ", "}")
                .replace(" <", "<")
                .replace(" {", "{")
            )
            result.append(s)
            result.append(sub_parts[1])

        return "".join(result)


# ---- Public API ----

# Backward-compatible alias for external callers
ConwertToHtml = IhtmlToHtml


def ihtml_to_html_base(
    file_name: Optional[str] = None, input_str: Optional[str] = None, lang: str = "en"
) -> str:
    """Convert ihtml source to standard HTML.

    Args:
        file_name: Path to ihtml file (or None to use input_str).
        input_str: ihtml source string (used when file_name is None).
        lang: Language code for translation (default 'en').

    Returns:
        Converted HTML string, or empty string on error.
    """
    converter = IhtmlToHtml(
        file_name,
        simple_close_tags=["br", "meta", "input"],
        auto_close_tags=[],
        no_auto_close_tags=[],
        input_str=input_str,
        lang=lang,
    )
    try:
        converter.process()
        return converter.to_str()
    except Exception:
        logger.exception("Error converting ihtml to HTML")
        return ""


def _py_to_js_wrapper(script: str) -> str:
    """Compile Python script to JavaScript with ihtml template support.

    Removes common indentation before compilation. Handles triple-quoted
    strings by compiling their ihtml content separately.

    Args:
        script: Python source code string.

    Returns:
        Compiled JavaScript code string.
    """
    # Remove common leading whitespace
    tab = -1
    out_tab = []
    for line in script.split("\n"):
        if tab < 0:
            if line.strip() != "":
                tab = len(line) - len(line.lstrip())
            else:
                continue
        out_tab.append(line[tab:])
    script2 = "\n".join(out_tab)

    spec_format = False

    if '"""' in script2:
        spec_format = True
        x = script2.split('"""')
        tab_script = []
        tab_string = []
        in_tabstring = False

        for pos in x:
            if in_tabstring:
                converted = ihtml_to_html_base(None, pos)
                converted = (
                    converted.replace("\r", "").replace("'", "\\'").replace('"', '\\"')
                )
                tab_string.append(converted)
                tab_script.append("'$$$compiled_str$$$'")
                in_tabstring = False
            else:
                tab_script.append(pos)
                in_tabstring = True

        script2 = "".join(tab_script)

        # Build multi-line string literals for the converted content
        tmp = []
        for pos in tab_string:
            split_pos = pos.split("\n")
            if len(split_pos) == 1:
                tmp.append(split_pos[0])
            elif len(split_pos) == 2:
                tmp.append(split_pos[0] + "\\n' +\n    '" + split_pos[1])
            else:
                result = split_pos[0] + "\\n' +\n"
                for line_part in split_pos[1:-1]:
                    result += "    '" + line_part + "\\n' +\n"
                result += "    '" + split_pos[-1]
                tmp.append(result)

        tab_string = tmp

    error, code = py_to_js_compile(script2)

    if error:
        logger.warning("Python-to-JS compilation error: %s", code)
        return code
    else:
        if spec_format:
            code = code.replace('"$$$compiled_str$$$"', "'$$$compiled_str$$$'")
            x = code.split("$$$compiled_str$$$")
            result = [None] * (len(x) + len(tab_string))
            result[::2] = x
            result[1::2] = tab_string
            code = "".join(result)
        return code


# Backward-compatible alias for external callers.
# Used by: schmanage/schbuilder/views.py, schdevtools/schbuilder/views.py
py_to_js = _py_to_js_wrapper
