from pytigon_lib.schhtml.parser import Parser
from io import StringIO


def divide(txt: str, width: int) -> list[str]:
    """Split text into lines of maximum width while preserving words.

    Args:
        txt: Text to divide into lines
        width: Maximum line width

    Returns:
        List of text lines
    """
    tab = []
    txt = txt.replace("\n", " ").lstrip()
    while True:
        if len(txt) < width:
            tab.append(txt)
            break
        x = txt[:width]
        if x.endswith(" ") or txt[width] == " ":
            txt = txt[width:].lstrip()
            tab.append(x.rstrip())
        else:
            y = x.rsplit(" ", 1)
            if len(y[0]) > 0:
                tab.append(y[0].rstrip())
                txt = txt[len(y[0]) :].lstrip()
            else:
                tab.append(x)
                txt = txt[width:].lstrip()
    return tab


class Html2IhtmlParser(Parser):
    """HTML parser that converts HTML to indented text format.

    The parser maintains indentation levels and handles special cases for
    script/style tags while writing to an output stream.
    """

    def __init__(self, out_stream, width: int = 80):
        """Initialize parser with output stream and formatting width.

        Args:
            out_stream: File-like object for writing output
            width: Maximum line width for text wrapping
        """
        super().__init__()
        self.out_stream = out_stream
        self.in_tag = []
        self.level = 0
        self.width = width
        self.in_script = False
        self.last_line_len = 999

    def _write_line(self, content: str) -> None:
        """Write a line to the output stream with proper line ending.

        Args:
            content: Content to write
        """
        self.out_stream.write(content + "\n")
        self.last_line_len = len(content)

    def handle_starttag(self, tag: str, attrib: dict) -> None:
        """Handle the start tag of an element.

        Args:
            tag: HTML tag name
            attrib: Dictionary of tag attributes
        """
        self.in_tag.append(tag)
        indent = " " * 4 * self.level
        attrs = (
            ",,,".join([f"{key}={value}" for key, value in attrib.items()])
            if attrib
            else ""
        )
        self._write_line(f"{indent}{tag} {attrs}".rstrip())

        if tag.lower() in ("style", "script"):
            self.in_script = True
        self.level += 1

    def handle_data(self, txt: str) -> None:
        """Handle the text data within an element.

        Args:
            txt: Text content to process
        """
        if not txt.strip():
            return

        indent = " " * 4 * self.level
        if self.in_script:
            self._write_line(f"{indent}>>>")
            self._write_line(txt)
            self._write_line(f"{indent}<<<")
        else:
            width = max(20, self.width - 4 * self.level)
            # if len(txt) < width - self.last_line_len:
            #    self._write_line(f"[[DEL]]...{txt.replace('\n', ' ').strip()}")
            if len(txt) < width:
                self._write_line(f"{indent}.{txt.replace('\n', ' ').strip()}")
            else:
                for line in divide(txt, width):
                    self._write_line(f"{indent}.{line}")

    def handle_endtag(self, tag: str) -> None:
        """Handle the end tag of an element.

        Args:
            tag: HTML tag name
        """
        self.level -= 1
        if self.in_script:
            self.in_script = False
        self.in_tag.pop()


def convert(file_name_in: str, file_name_out: str) -> None:
    """Convert HTML file to indented text format.

    Args:
        file_name_in: Input HTML file path
        file_name_out: Output file path
    """
    buf = StringIO()
    with open(file_name_in, "rt") as f_in, open(file_name_out, "wt") as f_out:
        parser = Html2IhtmlParser(buf, 256)
        parser.feed(f_in.read())
        f_out.write(buf.getvalue())
        # f_out.write(buf.getvalue().replace("\n[[DEL]]", "").replace("[[DEL]]", ""))


if __name__ == "__main__":
    convert("test.html", "test.ihtml")
