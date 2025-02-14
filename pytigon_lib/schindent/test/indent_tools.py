from html.parser import HTMLParser
import io


def _convert_strings(lines):
    """Convert strings in the input lines, handling multi-line strings."""
    line_buf = None
    in_string = False
    lines.seek(0)
    for line in lines:
        line = line.replace("\n", "")
        id = line.find('"""')
        if in_string:
            if id >= 0:
                yield line_buf + "\n" + line
                line_buf = None
                in_string = False
            else:
                line_buf = (line_buf + line) if line_buf else line
        else:
            if line.lstrip().startswith("#"):
                continue
            if id >= 0:
                id2 = line[id:].find('"""')
                if id2 >= 0:
                    yield (line_buf + line) if line_buf else line
                    line_buf = None
                else:
                    in_string = True
                    line_buf = (line_buf + "\n" + line) if line_buf else line
            else:
                yield line
                line_buf = None


def spaces_count(s):
    """Count the number of leading spaces in a string."""
    return len(s) - len(s.lstrip(" "))


def norm_tab(f):
    """Normalize tabs and spaces in the input file."""
    old_il = 0
    poziom = 0
    tabpoziom = [0]
    tabkod = []
    for l in _convert_strings(f):
        line = l.replace("\t", " " * 8).rstrip()
        if not line.lstrip():
            continue
        il = spaces_count(line)
        if il > old_il:
            poziom += 1
            tabpoziom.append(il)
        else:
            while il < tabpoziom[-1]:
                poziom -= 1
                tabpoziom.pop()
        if line[il:]:
            tabkod.append((poziom, line[il:]))
        old_il = il
    return tabkod


def reformat_js(tabkod):
    """Reformat JavaScript code."""
    postfixs = [(0, "", ";")]
    tabkod2 = []
    for pos in tabkod:
        code = pos[1]
        postfix = ""
        if code.startswith("def ") and code.endswith(":"):
            code = "function " + code[4:]
        if code.endswith("({"):
            postfix = "})"
            code = code[:-2] + "({"
        elif code.endswith("("):
            postfix = ")"
            code = code[:-1] + "("
        elif code.endswith("["):
            postfix = "];"
            code = code[:-1] + "["
        elif code.endswith("[,"):
            postfix = "],"
            code = code[:-2] + "["
        elif code.endswith(":"):
            postfix = "}"
            code = code[:-1] + "{"
        elif code.endswith("/:"):
            code = code[:-2]
        elif code.endswith("="):
            postfix = "}"
            code = code[:-1] + "= {"
        elif code.endswith("{"):
            postfix = "}"
            code = code[:-1] + "{"
        tabkod2.append((pos[0], code, postfix, "," if postfix else ""))
    tabkod3 = []
    oldpoziom = 0
    for pos in tabkod2:
        if pos[0] <= oldpoziom:
            for _ in range(oldpoziom - pos[0] + 1):
                tabkod3.append((postfixs[-1][0], postfixs[-1][1], ""))
                postfixs.pop()
        tabkod3.append((pos[0], pos[1], postfixs[-1][2] if len(pos[2]) == 0 else ""))
        postfixs.append((pos[0], pos[2], pos[3]))
        oldpoziom = pos[0]
    for i in range(len(postfixs) - 1, 0, -1):
        tabkod3.append((postfixs[i][0], postfixs[i][1], postfixs[i - 1][2]))
    tabkod3 = [pos for pos in tabkod3 if pos[1]]
    tabkod4 = []
    for i, pos in enumerate(tabkod3):
        if i < len(tabkod3) - 1 and pos[0] > tabkod3[i + 1][0]:
            tabkod4.append((pos[0], pos[1]))
        else:
            tabkod4.append((pos[0], pos[1] + pos[2]))
    return tabkod4


def file_norm_tab(file_in, file_out):
    """Normalize tabs in a file and write to another file."""
    if file_in and file_out:
        tabkod = norm_tab(file_in)
        for pos in tabkod:
            file_out.write(" " * 4 * pos[0] + pos[1] + "\n")
        return True
    return False


def convert_js(stream_in, stream_out):
    """Convert and reformat JavaScript code."""
    if stream_in and stream_out:
        tabkod = norm_tab(stream_in)
        tabkod = reformat_js(tabkod)
        for pos in tabkod:
            stream_out.write(
                " " * 4 * pos[0] + pos[1].replace("};", "}").replace(";;", ";") + "\n"
            )
        return True
    return False


class NormParser(HTMLParser):
    """HTML parser for normalizing HTML content."""

    def __init__(self):
        super().__init__()
        self.txt = io.StringIO()
        self.tab = 0

    def _remove_spaces(self, value):
        return value.strip()

    def _print_attr(self, attr):
        return ",,,".join(f"{k}={v}" if v else k for k, v in attr)

    def handle_starttag(self, tag, attrs):
        self.txt.write("\n" + " " * 4 * self.tab + tag + " " + self._print_attr(attrs))
        self.tab += 1

    def handle_endtag(self, tag):
        self.tab -= 1

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_data(self, data):
        if self._remove_spaces(data):
            self.txt.write("..." + self._remove_spaces(data).replace("\n", "\\n"))

    def process(self, data):
        try:
            self.feed(data)
        except Exception as e:
            print(f"Error processing HTML: {e}")
            return data
        return self.txt.getvalue()[1:] + "\n"


class IndentHtmlParser(NormParser):
    """HTML parser for indenting HTML content."""

    def handle_starttag(self, tag, attrs):
        self.txt.write("\n" + " " * 4 * self.tab + self.get_starttag_text())
        self.tab += 1

    def handle_endtag(self, tag):
        self.tab = max(self.tab - 1, 0)
        self.txt.write("\n" + " " * 4 * self.tab + f"</{tag}>\n")

    def handle_data(self, data):
        if data.strip():
            self.txt.write("\n" + " " * 4 * self.tab + data.strip())


def norm_html(txt):
    """Normalize HTML content."""
    try:
        n = NormParser()
        return n.process(txt)
    except Exception as e:
        print(f"Error normalizing HTML: {e}")
        return txt


def indent_html(txt):
    """Indent HTML content."""
    try:
        n = IndentHtmlParser()
        ret = n.process(txt)
        return "\n".join(line for line in ret.split("\n") if line.strip())
    except Exception as e:
        print(f"Error indenting HTML: {e}")
        return txt
