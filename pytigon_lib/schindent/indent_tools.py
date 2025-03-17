import io
from pytigon_lib.schparser.parser import Parser


def _convert_strings(lines):
    """Convert multi-line strings into single lines."""
    line_buf = None
    in_string = False
    lines.seek(0)
    for line in lines:
        line = line.rstrip("\n")
        id = line.find('"""')
        if in_string:
            if id >= 0:
                yield f"{line_buf}\n{line}"
                line_buf = None
                in_string = False
            else:
                line_buf = f"{line_buf}\n{line}" if line_buf else line
        else:
            if id >= 0:
                id2 = line[id:].find('"""')
                if id2 >= 0:
                    yield f"{line_buf}{line}" if line_buf else line
                    line_buf = None
                else:
                    in_string = True
                    line_buf = f"{line_buf}\n{line}" if line_buf else line
            else:
                yield line
                line_buf = None


def spaces_count(s):
    """Count the number of leading spaces in a string."""
    return len(s) - len(s.lstrip(" "))


def norm_tab(f):
    """Normalize indentation in the file."""
    old_il = 0
    poziom = 0
    tabpoziom = [0]
    tabkod = []
    for line in _convert_strings(f):
        line = line.replace("\t", " " * 8).rstrip()
        if not line.strip():
            continue
        il = spaces_count(line)
        if il > old_il:
            poziom += 1
            tabpoziom.append(il)
        elif il < old_il:
            while il < tabpoziom[-1]:
                poziom -= 1
                tabpoziom.pop()
        if line[il:]:
            tabkod.append((poziom, line[il:]))
        old_il = il
    return tabkod


def reformat_js(tabkod):
    """Reformat JavaScript code."""
    tabkod2 = []
    sep = ""
    for pos in tabkod:
        code = pos[1]
        postfix = ""
        if code[:4] == "def " and code[-1] == ":":
            code = "function " + code[4:]
        if code.endswith("({"):
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
            sep = ";"
            code = code[:-1] + "{"
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
        tabkod2.append((pos[0], code, postfix, sep))

    tabkod2.append([0, "", "", ""])
    tabkod3 = []
    stack = []

    for pos in tabkod2:
        while len(stack) > 0:
            if pos[0] > stack[-1][0]:
                stack.append(pos)
                break
            top = stack.pop()
            if pos[0] == top[0]:
                if len(stack) > 0:
                    x = stack[-1][3]
                else:
                    x = ";"
                tabkod3[-1][1] += x
            else:
                if len(stack) > 0:
                    tabkod3.append([stack[-1][0], stack[-1][2]])
        tabkod3.append([pos[0], pos[1]])
        if len(stack) == 0:
            stack.append(pos)

    return tabkod3


def file_norm_tab(file_in, file_out):
    """Normalize tabs in a file and write to another file."""
    if file_in and file_out:
        tabkod = norm_tab(file_in)
        for pos in tabkod:
            file_out.write(f"{' ' * 4 * pos[0]}{pos[1]}\n")
        return True
    return False


def convert_js(stream_in, stream_out):
    """Convert Python-like code to JavaScript and write to a stream."""
    if stream_in and stream_out:
        tabkod = norm_tab(stream_in)
        tabkod = reformat_js(tabkod)
        for pos in tabkod:
            stream_out.write(
                f"{' ' * 4 * pos[0]}{pos[1].replace('};', '}').replace(';;', ';')}\n"
            )
        return True
    return False


class NormParser(Parser):
    """Parser for normalizing HTML."""

    def __init__(self):
        self.txt = io.StringIO()
        self.tab = 0
        super().__init__()

    def _remove_spaces(self, value):
        return value.strip()

    def _print_attr(self, attr):
        return ",,,".join(f"{k}={v}" if v else k for k, v in attr)

    def handle_starttag(self, tag, attrs):
        self.txt.write(f"\n{' ' * self.tab * 4}{tag} {self._print_attr(attrs)}")
        self.tab += 1

    def handle_endtag(self, tag):
        self.tab -= 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data):
        if self._remove_spaces(data):
            self.txt.write(f"...{self._remove_spaces(data).replace('\n', '\\n')}")

    def process(self, data):
        self.feed(data)
        return self.txt.getvalue()


class IndentHtmlParser(NormParser):
    """Parser for indenting HTML."""

    def handle_starttag(self, tag, attrs):
        self.txt.write(f"\n{' ' * self.tab * 4}{self.get_starttag_text()}")
        self.tab += 1

    def handle_endtag(self, tag):
        self.tab = max(self.tab - 1, 0)
        self.txt.write(f"\n{' ' * self.tab * 4}</{tag}>\n")

    def handle_data(self, data):
        if data.strip():
            self.txt.write(f"\n{' ' * self.tab * 4}{data.strip()}")


def norm_html(txt):
    """Normalize HTML content."""
    n = NormParser()
    return n.process(txt)


def indent_html(txt):
    """Indent HTML content."""
    try:
        n = IndentHtmlParser()
        ret = n.process(txt)
        lines = [line for line in ret.split("\n") if line.strip()]
        return "\n".join(lines)
    except Exception:
        return txt


if __name__ == "__main__":
    if False:
        with (
            open("./test/test11.html", "r") as f_in,
            open("./test/test11.ihtml", "w") as f_out,
        ):
            ret = norm_html(f_in.read())
            f_out.write(ret)

    if True:
        with (
            open("./test/test11.ihtml", "r") as f_in,
            open("./test/_test11.html", "w") as f_out,
        ):
            ret = indent_html(f_in.read())
            f_out.write(ret)
