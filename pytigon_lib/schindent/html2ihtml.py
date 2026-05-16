"""
HTML to indented text format (ihtml) converter.

Converts HTML files to a human-readable indented text format where:
- Each HTML tag is written at its indentation level
- Attributes use ,,, as separator
- Text content is prefixed with '.'
- Script/style blocks are marked with >>> and <<< delimiters
- End tags are represented as $$$ markers
"""

import logging
import re
from typing import List, TextIO

from pytigon_lib.schparser.parser import Parser

logger = logging.getLogger(__name__)

# Tags whose content should not be word-wrapped
_PRESERVE_WHITESPACE_TAGS = frozenset({"style", "script", "pre", "textarea", "code"})

# End-of-block sentinel marker
_END_MARKER = "$$$"

# Content prefix for text lines
_CONTENT_PREFIX = "."

# Attribute separator
_ATTR_SEPARATOR = ",,,"


def divide(txt: str, width: int) -> List[str]:
    """Split text into lines of maximum width while preserving word boundaries.

    Words longer than the specified width are placed on their own line.

    Args:
        txt: Text to divide into lines.
        width: Maximum line width in characters.

    Returns:
        List of text lines, each not exceeding the specified width.
    """
    lines = []
    txt = txt.replace("\n", " ").lstrip()

    while txt:
        if len(txt) <= width:
            lines.append(txt)
            break

        segment = txt[:width]

        if segment.endswith(" ") or txt[width] == " ":
            # Natural break at space
            txt = txt[width:].lstrip()
            lines.append(segment.rstrip())
        else:
            # Try to break at last space within width
            parts = segment.rsplit(" ", 1)
            if len(parts[0]) > 0:
                lines.append(parts[0].rstrip())
                txt = txt[len(parts[0]) :].lstrip()
            else:
                # Word is longer than width, take it as-is
                lines.append(segment)
                txt = txt[width:].lstrip()

    return lines


class Html2IhtmlParser(Parser):
    """HTML parser that converts HTML to indented text format (ihtml).

    Produces output where each line has the format:
        <indent><tag> <attrs>       for opening tags
        <indent>.<text>              for text content
        $$$                          for closing tags

    Script and style content is delimited by >>> and <<< markers.

    Attributes:
        out_stream: File-like object for writing final output.
        level: Current indentation level (0-based).
        width: Maximum line width for text wrapping.
    """

    def __init__(self, out_stream: TextIO, width: int = 80) -> None:
        """Initialize parser with output stream and formatting options.

        Args:
            out_stream: File-like object for writing output.
            width: Maximum line width for text wrapping (default 80).
        """
        super().__init__()
        self.out_stream = out_stream
        self.out_tab: List[List] = []
        self.in_tag: List[str] = []
        self.level = 0
        self.width = width
        self.in_script = False
        self.last_line_len = 999

    def _write_line(self, content: str) -> None:
        """Record a line at the current indentation level.

        Args:
            content: Line content to write.
        """
        self.out_tab.append([self.level, content])
        self.last_line_len = len(content)

    def handle_starttag(self, tag: str, attrib: dict) -> None:
        """Handle an opening HTML tag.

        Args:
            tag: HTML tag name.
            attrib: Dictionary of tag attributes.
        """
        self.in_tag.append(tag)
        indent = " " * 4 * self.level

        attrs = ""
        if attrib:
            attrs = _ATTR_SEPARATOR.join(
                f"{key}={value}" for key, value in attrib.items()
            )

        self._write_line(f"{indent}{tag} {attrs}".rstrip())

        if tag.lower() in ("style", "script"):
            self.in_script = True
        self.level += 1

    def handle_data(self, txt: str) -> None:
        """Handle text content within an element.

        Normalizes whitespace for most tags, preserves whitespace for
        code/preformatted tags. Wraps long text to fit within width.

        Args:
            txt: Text content to process.
        """
        if not txt.strip():
            return

        # Normalize whitespace for non-code tags
        current_tag = self.in_tag[-1].lower() if self.in_tag else ""
        if current_tag not in _PRESERVE_WHITESPACE_TAGS:
            txt = re.sub(r" +", " ", txt.replace("\n", " "))

        indent = " " * 4 * self.level

        if self.in_script:
            self._write_line(f"{indent}>>>")
            self._write_line(txt)
            self._write_line(f"{indent}<<<")
        else:
            available_width = max(20, self.width - 4 * self.level)

            if len(txt) < available_width:
                self._write_line(
                    f"{indent}{_CONTENT_PREFIX}{txt.replace('\n', ' ').strip()}"
                )
            else:
                for line in divide(txt, available_width):
                    self._write_line(f"{indent}{_CONTENT_PREFIX}{line}")

    def handle_endtag(self, tag: str) -> None:
        """Handle a closing HTML tag.

        Args:
            tag: HTML tag name.
        """
        self.level -= 1
        if self.in_script:
            self.in_script = False
        self.in_tag.pop()
        self._write_line(_END_MARKER)

    def close(self) -> None:
        """Finalize parsing and write output.

        Performs post-processing to merge short text lines that follow
        an opening tag onto the same line, then writes clean output.
        """
        super().close()

        # Post-process: merge short text lines after opening tags
        for i in range(len(self.out_tab)):
            level, line = self.out_tab[i]
            line = line.strip()

            if line == _END_MARKER:
                continue

            # Check if this is a short text line immediately after an opening tag
            # with enough room on the previous line, and at a deeper level
            prev_exists = i > 0
            if not prev_exists:
                continue

            prev_level, prev_line = self.out_tab[i - 1]
            is_text_line = line.startswith(_CONTENT_PREFIX)
            is_deeper = level > prev_level
            fits_on_prev = (len(prev_line) + len(line)) < self.width
            is_last_or_back = (
                i >= len(self.out_tab) - 1 or level > self.out_tab[i + 1][0]
            )

            if is_text_line and is_deeper and fits_on_prev and is_last_or_back:
                # Merge into previous line with double-dot separator
                self.out_tab[i][1] = _END_MARKER
                self.out_tab[i - 1][1] += f"..{line.strip()}"

        # Write non-sentinel lines to output
        output_lines = [
            item[1] for item in self.out_tab if item[1].strip() != _END_MARKER
        ]
        self.out_stream.write("\n".join(output_lines))


def convert(file_name_in: str, file_name_out: str) -> None:
    """Convert an HTML file to indented text (ihtml) format.

    Args:
        file_name_in: Path to the input HTML file.
        file_name_out: Path for the output ihtml file.

    Raises:
        FileNotFoundError: If the input file does not exist.
        OSError: If file operations fail.
    """
    with (
        open(file_name_in, encoding="utf-8") as f_in,
        open(file_name_out, "w", encoding="utf-8") as f_out,
    ):
        parser = Html2IhtmlParser(f_out, 256)
        parser.feed(f_in.read())
        parser.close()


if __name__ == "__main__":
    convert("test.html", "test.ihtml")
