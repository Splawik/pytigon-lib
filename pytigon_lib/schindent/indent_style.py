import os
import io
import gettext
import codecs
from pytigon_lib.schindent.py_to_js import compile
from pytigon_lib.schtools.tools import norm_indent
from .indent_tools import convert_js
from django.conf import settings
from pytigon_lib.schtools.main_paths import get_main_paths, get_prj_name

try:
    import markdown

    def convert_md(stream_in, stream_out):
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

except ImportError:
    pass


def list_with_next_generator(lst):
    old = lst[0]
    for pos in lst[1:]:
        yield (old, pos)
        old = pos
    yield (lst[-1], None)


def translate(s):
    return s


def iter_lines(f, f_name, lang):
    base_path = os.path.join(settings.PRJ_PATH, get_prj_name())
    locale_path = os.path.join(base_path, "locale")
    tab_translate = []

    if f:
        f2 = f
    else:
        f2 = open(f_name, "rt", encoding="utf-8")

    if lang != "en":
        try:
            t = gettext.translation("django", locale_path, languages=[lang])
            t.install()
        except:
            t = None

        try:
            with open(
                os.path.join(base_path, "translate.py"), "rt", encoding="utf-8"
            ) as p:
                for line in p.readlines():
                    fr = line.split('_("')
                    if len(fr) > 1:
                        fr = fr[1].split('")')
                        if len(fr) == 2:
                            tab_translate.append(fr[0])
        except:
            tab_translate = []

        def trans(word):
            if len(word) < 2:
                return word
            if word[0] == word[-1] == '"' or word[0] == word[-1] == "'":
                strtest = word[0]
                word2 = word[1:-1]
            else:
                strtest = None
                word2 = word

            if word2 not in tab_translate:
                tab_translate.append(word2)
            if t:
                ret = t.gettext(word2)
                return f"{strtest}{ret}{strtest}" if strtest else ret
            return translate(word)

        gt = trans
    else:
        gt = translate

    for line in f2:
        if line.lstrip().startswith("_") and not line.lstrip().startswith("_("):
            nr = line.find("_")
            line2 = " " * nr + "." + gt(line.strip()[1:])
        else:
            if "_(" in line and not "__(" in line:
                out = []
                if line.lstrip().startswith("_("):
                    fr0 = line.split("_(")
                    fr = (fr0[0] + ".", fr0[1])
                else:
                    fr = line.split("_(")
                out.append(fr[0])
                for pos in fr[1:]:
                    id2 = pos.find(")")
                    if id2 >= 0:
                        out.append(gt(pos[:id2]))
                        out.append(pos[id2 + 1 :])
                    else:
                        out.append(gt(pos))
                line2 = "".join(out)
            else:
                line2 = line

        yield line2
    if not f:
        f2.close()
    yield "."

    if tab_translate and "site-packages" not in base_path:
        try:
            with open(
                os.path.join(base_path, "translate.py"), "wt", encoding="utf-8"
            ) as p:
                for word in tab_translate:
                    p.write(f'_("{word}")\n')
        except Exception as e:
            print(f"Error writing translation file: {e}")


class ConwertToHtml:
    def __init__(
        self,
        file_name,
        simple_close_elem,
        auto_close_elem,
        no_auto_close_elem,
        input_str=None,
        lang="en",
        output_processors=None,
    ):
        self.file_name = file_name
        self.input_str = input_str
        self.code = []
        self.bufor = []
        self.output = []
        self.no_conwert = False
        self.simple_close_elem = simple_close_elem
        self.auto_close_elem = auto_close_elem
        self.no_auto_close_elem = no_auto_close_elem
        self.lang = lang
        self.output_processors = output_processors

    def _output_buf(self, nr):
        for pos in reversed(self.bufor):
            if pos[0] >= nr:
                self.output.append([pos[0], pos[1], pos[2]])
                self.bufor.remove(pos)
            else:
                break

    def _space_count(self, buf):
        return len(buf) - len(buf.lstrip())

    def _get_elem(self, elem):
        elem2 = elem.lstrip()
        id = elem2.find(" ")
        return elem2[:id] if id > 0 else elem2

    def _transform_elem(self, elem):
        id = elem.find(" ")
        if id > 0:
            elem0 = elem[:id]
            elem1 = ""
            tmp = elem[id + 1 :].split(",,,")
            for pos in tmp:
                id2 = pos.find("=")
                if id2 > 0:
                    elem1 = elem1 + " " + pos[:id2] + '="' + pos[id2 + 1 :] + '"'
                else:
                    elem1 = elem1 + " " + pos
            return elem0 + elem1
        else:
            return elem

    def _pre_process_line(self, line):
        n = self._space_count(line)
        line2 = line[n:]
        if line2.rstrip() == "":
            return [None]
        if not (
            (line2[0] >= "a" and line2[0] <= "z")
            or (line2[0] >= "A" and line2[0] <= "Z")
            or line2[0] == "%"
        ):
            if line2[0] == ".":
                return [(n, None, line2[1:], 0)]
            else:
                return [(n, None, line2, 0)]
        nr = line2.find("...")
        if nr >= 0:
            code = line2[:nr]
            html = line2[nr + 3 :]
            if code == "":
                code = None
        else:
            code = line2
            html = None
        if code:
            if code[0] != "%":
                code2 = code.split(":::")
                if len(code2) > 1:
                    out = []
                    i = n
                    for pos in code2[:-1]:
                        out.append(
                            (i, self._transform_elem(pos), None, 3 if i == n else 1)
                        )
                        i = i + 1
                    out.append((i, self._transform_elem(code2[-1]), html, 4))
                    return out
                else:
                    code = self._transform_elem(code)
        return [(n, code, html, 0)]

    def transform_line(self, line, next_line):
        if not (line[1] is None and line[2] is None):
            self._output_buf(line[0])

        if line[1]:
            if line[1][0] == "%":
                if line[1][1] == "%":
                    if next_line[0] <= line[0] and not (
                        next_line[1] is None and next_line[2] is None
                    ):
                        self.output.append(
                            [
                                line[0],
                                f"{{% block {line[1][2:].lstrip()} %}}{line[2] if line[2] else ''}{{% endblock %}}",
                                line[3],
                            ]
                        )
                    else:
                        self.output.append(
                            [line[0], f"{{% block {line[1][2:].lstrip()} %}}", line[3]]
                        )
                        if line[2]:
                            self.output.append([line[0], line[2], line[3]])
                        self.bufor.append([line[0], "{% endblock %}", line[3]])
                else:
                    auto_end = False
                    tag = line[1][1:].split()[0].strip()
                    full_tag = line[1][1:].strip()
                    # auto_end = (
                    #    full_tag.endswith(":") and tag not in self.no_auto_close_elem
                    # )
                    if full_tag.endswith(":"):
                        auto_end = True
                        tag = tag.replace(":", "")
                        full_tag = full_tag[:-1]
                        if tag in self.no_auto_close_elem:
                            auto_end = False

                    self.output.append([line[0], f"{{% {full_tag} %}}", line[3]])
                    if auto_end or tag in self.auto_close_elem or "_ext" in tag:
                        self.bufor.append([line[0], f"{{% end{tag} %}}", line[3]])
                    if line[2]:
                        self.output.append([line[0], line[2], line[3]])
            else:
                if next_line[0] <= line[0] and not (
                    next_line[1] is None and next_line[2] is None
                ):
                    if line[2] or self._get_elem(line[1]) not in self.simple_close_elem:
                        s = line[2] if line[2] else ""
                        self.output.append(
                            [
                                line[0],
                                f"<{line[1]}>{s}</{self._get_elem(line[1])}>",
                                line[3],
                            ]
                        )
                    else:
                        self.output.append([line[0], f"<{line[1]} />", line[3]])
                else:
                    self.output.append([line[0], f"<{line[1]}>", line[3]])
                    if line[2]:
                        self.output.append([line[0], line[2], line[3]])
                    self.bufor.append(
                        [line[0], f"</{self._get_elem(line[1])}>", line[3]]
                    )
        else:
            self.output.append([line[0], line[2], line[3]])

    def transform(self):
        old_line = None
        for line in self.code:
            if old_line is not None:
                self.transform_line(old_line, line)
            old_line = line
        if old_line:
            self.transform_line(old_line, (0, None, None))
        self._output_buf(-1)

    def process(self):
        if self.file_name:
            file1 = codecs.open(self.file_name, "r", encoding="utf-8")
            x = file1.readline()
            file1.seek(0, 0)
            if x.startswith("@@@"):
                fname = x[3:].strip()
                fpath = os.path.join(os.path.dirname(self.file_name), fname) + ".ihtml"
                with codecs.open(fpath, "r", encoding="utf-8") as file2:
                    content2 = file1.read()[len(x) :]
                    content = file2.read().replace("@@@", content2)
                file = io.StringIO(content)
                file1.close()
            else:
                file = file1
        else:
            file = io.StringIO(self.input_str)

        old_pos = 0
        buf = None
        buf0 = ""
        test = 0
        cont = False
        indent_pos = 0

        for _line in iter_lines(file, self.file_name, self.lang):
            line = _line.replace("\n", "").replace("\r", "").replace("\t", "        ")
            if line.replace(" ", "") in ("%else", "%else:"):
                line = " " + line
            if "^^^" in line:
                self.no_conwert = True
                return

            if test:
                if (
                    test > 1
                    and len(line.strip()) > 0
                    and self._space_count(line) <= indent_pos
                ):
                    cont = True
                if cont or "<<<" in line:
                    if test == 1:
                        l = line.replace("<<<", "").rstrip()
                        buf.write(l)
                        x = self._pre_process_line(buf0 + buf.getvalue())
                        for pos in x:
                            if pos:
                                self.code.append((pos[0] * 4, pos[1], pos[2], pos[3]))
                                old_pos = pos[0]
                            else:
                                self.code.append((old_pos * 4, None, None, 1))
                        buf = None
                        test = 0
                        continue
                    if test > 1:
                        if not cont:
                            l = line.replace("<<<", "").rstrip()
                            buf.write(l)
                        if test == 2:
                            buf2 = io.StringIO()
                            convert_js(buf, buf2)
                            x = self._pre_process_line(buf0 + buf2.getvalue())
                        elif test == 3:
                            x = self._pre_process_line(
                                buf0.replace("pscript", "script language=python")
                                + buf.getvalue()
                            )
                            test = 0
                        elif test == 4:
                            v = buf.getvalue()
                            codejs = py_to_js(v, None)
                            x = self._pre_process_line(
                                buf0.replace("pscript", "script").replace(
                                    " language=python", ""
                                )
                                + codejs
                            )
                        elif test == 5:
                            v = buf.getvalue()
                            codejs = py_to_js(v, None)
                            x = self._pre_process_line(
                                buf0.replace("pscript", "script").replace(
                                    " language=python", ""
                                )
                                + codejs
                            )
                        elif test == 6:
                            buf2 = io.StringIO()
                            convert_md(buf, buf2)
                            x = self._pre_process_line(buf0 + buf2.getvalue())
                        else:
                            x = self._pre_process_line(buf0 + buf.getvalue())
                        for pos in x:
                            if pos:
                                self.code.append((pos[0] * 4, pos[1], pos[2], pos[3]))
                                old_pos = pos[0]
                            else:
                                self.code.append((old_pos * 4, None, None, 1))
                        buf = None
                        buf2 = None
                        test = 0
                else:
                    buf.write(line.rstrip() + "\n")
                    continue
            if cont or not test:
                cont = False
                if ">>>" in line:
                    pos = line.find(">>>")
                    buf0 = line[: pos + 3].replace(">>>", "...|||")
                    buf = io.StringIO()
                    buf.write(line[pos + 3 :].rstrip())
                    test = 1
                elif "{:}" in line:
                    indent_pos = self._space_count(line)
                    pos = line.find("{:}")
                    buf0 = line[: pos + 4].replace("{:}", "...|||")
                    buf = io.StringIO()
                    buf.write(line[pos + 4 :].rstrip())
                    test = 2
                elif "===>" in line:
                    indent_pos = self._space_count(line)
                    pos = line.find("===>")
                    buf0 = line[: pos + 4].replace("===>", "...|||")
                    buf = io.StringIO()
                    buf.write(line[pos + 4 :].rstrip())
                    test = 3
                elif "script language=python" in line:
                    indent_pos = self._space_count(line)
                    pos = line.find("script language=python")
                    buf0 = line + "...|||"
                    buf = io.StringIO()
                    buf.write(line[pos + 22 :].rstrip())
                    test = 3
                elif "pscript" in line:
                    indent_pos = self._space_count(line)
                    buf0 = line + "...|||"
                    buf = io.StringIO()
                    test = 3
                elif line.strip().replace(" ", "") == "script":
                    indent_pos = self._space_count(line)
                    buf0 = line + "...|||"
                    buf = io.StringIO()
                    test = 4
                elif line.strip().replace(" ", "").startswith("%component"):
                    indent_pos = self._space_count(line)
                    pos = line.rfind(":")
                    buf0 = line + "...|||"
                    test = 5
                    buf = io.StringIO()
                elif "###>" in line:
                    indent_pos = self._space_count(line)
                    pos = line.find("###>")
                    buf0 = line[: pos + 4].replace("###>", "...|||")
                    buf = io.StringIO()
                    buf.write(line[pos + 4 :].rstrip())
                    test = 6
                else:
                    l = line.rstrip()
                    x = self._pre_process_line(l)
                    for pos in x:
                        if pos:
                            self.code.append((pos[0] * 4, pos[1], pos[2], pos[3]))
                            old_pos = pos[0]
                        else:
                            self.code.append((old_pos * 4, None, None, 1))
        self.code.append((0, None, None, 1))
        self.transform()

    def to_str(self, beauty=True):
        if self.no_conwert:
            if self.file_name:
                with codecs.open(self.file_name, "r", encoding="utf-8") as file:
                    output = file.read().replace("^^^", "")
            else:
                output = self.input_str.replace("^^^", "")
            output = output.replace("\r", "").replace("\\\n", "")
            return output
        else:
            output = ""
            if beauty:
                for line, nextline in list_with_next_generator(self.output):
                    if line[0] >= 0 and (line[2] == 0 or line[2] == 3):
                        output += " " * int(line[0] / 2)
                    if line[1]:
                        output += line[1]
                    if line[2] == 0 or line[2] == 2:
                        output += "\n"
                    if line[2] == 4 and nextline and nextline[0] > line[0]:
                        output += "\n"
                ret = output.replace("|||", "\n")
            else:
                for line, nextline in list_with_next_generator(self.output):
                    if line[0] >= 0 and line[2] == 3:
                        output += " " * int(line[0] / 2)
                    if line[1]:
                        output += line[1]
                    if line[2] == 2:
                        output += "\n"
                    elif line[2] == 4 and nextline and nextline[0] > line[0]:
                        output += "\n"
                    elif (
                        line[1]
                        and nextline[1]
                        and not (
                            line[1].strip().startswith("<")
                            or line[1].strip().startswith("{")
                        )
                        and not (
                            nextline[1].strip().startswith("<")
                            or nextline[1].strip().startswith("{")
                        )
                    ):
                        output += "\n"
                ret = output.replace("|||", "\n")

            if self.output_processors and "@@(" in ret:
                tab_tmp1 = ret.split("@@(")
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
                ret = "".join(ret2)

            ret = ret.replace("\r", "").replace("\\\n", "")
            return ret


def ihtml_to_html_base(file_name, input_str=None, lang="en"):
    conwert = ConwertToHtml(file_name, ["br", "meta", "input"], [], [], input_str, lang)
    try:
        conwert.process()
        return conwert.to_str()
    except Exception as e:
        print(f"Error during conversion: {e}")
        return ""


def py_to_js(script, module_path):
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
                pos2 = ihtml_to_html_base(None, pos)
                tab_string.append(
                    pos2.replace("\r", "").replace("'", "\\'").replace('"', '\\"')
                )
                tab_script.append("'$$$compiled_str$$$'")
                in_tabstring = False
            else:
                tab_script.append(pos)
                in_tabstring = True
        script2 = "".join(tab_script)
        tmp = []
        for pos in tab_string:
            tmp2 = pos.split("\n")
            if len(tmp2) == 1:
                tmp.append(tmp2[0])
            elif len(tmp2) == 2:
                tmp.append(tmp2[0] + "\\n' +\n    '" + tmp2[1])
            else:
                result = tmp2[0] + "\\n' +\n"
                for pos2 in tmp2[1:-1]:
                    result += "    '" + pos2 + "\\n' +\n"
                result += "    '" + tmp2[-1]
                tmp.append(result)
        tab_string = tmp

    error, code = compile(script2)

    if error:
        print(code)
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
