import json
import markdown
from django.template.loader import select_template

REG_OBJ_RENDERER = {}


class BaseObjRenderer:
    def __init__(self, extra_info=""):
        self.extra_info = extra_info

    @staticmethod
    def get_info():
        return {
            "name": "",
            "title": "",
            "icon": "",
            "show_form": False,
            "inline_content": False,
        }

    def get_edit_form(self):
        return None

    def convert_form_to_dict(self, form, old_dict=None):
        return form.cleaned_data

    def form_from_dict(self, form_class, param):
        if param:
            return form_class(initial=param)
        else:
            return form_class()

    def gen_context(self, param, lines):
        return {}

    def get_renderer_template_name(self):
        return None

    def get_edit_template_name(self):
        # return "schwiki/" + self.get_info()["name"].lower() + "_wikiobj_edit.html"
        return "schwiki/wikiobj_edit.html"

    def render(self, param, lines):
        template_name = self.get_renderer_template_name()
        context = self.gen_context(param, lines)
        if template_name:
            t = select_template(
                [
                    template_name,
                ]
            )
            return t.render(context)
        else:
            if context and "content" in context:
                return context["content"]
            else:
                return "[[[" + self.extra_info + "]]]"


def register_obj_renderer(obj_name, obj_renderer):
    if not obj_name in REG_OBJ_RENDERER:
        REG_OBJ_RENDERER[obj_name] = obj_renderer


def get_obj_renderer(obj_name):
    if obj_name in REG_OBJ_RENDERER:
        return REG_OBJ_RENDERER[obj_name]()
    else:
        return BaseObjRenderer(obj_name)


def get_indent(s):
    return len(s) - len(s.lstrip())


def unindent(lines):
    indent = -1
    for line in lines:
        if line:
            indent = get_indent(line)
            break
    if indent > 0:
        lines2 = []
        for line in lines:
            lines2.append(line[indent:])
        return lines2
    return lines


def markdown_to_html(buf):
    return markdown.markdown(
        buf,
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


class IndentMarkdownProcessor:
    def __init__(self):
        pass

    def _json_dumps(self, j):
        return json.dumps(j).replace("\n", "\\n")

    def _json_loads(self, s):
        if s and s[0] == "{":
            return json.loads(s.replace("\\n", "\n"))
        else:
            return s

    def _render_obj(self, config, lines):
        x = config.split("#", 1)
        if len(x) > 1:
            param = self._json_loads(x[1].strip())
        else:
            param = None

        obj_name = x[0].strip()[1:].strip()
        if obj_name.endswith(":"):
            obj_name = obj_name[:-1]
        return self.render_obj(obj_name, param, lines)
        # f1 = x[0].strip()
        # if len(f1) < 80:
        #    f2 = " " * (80 - len(f1))
        # else:
        #    f2 = ""
        # ret_str = f1 + f2 + "#" + self._json_dumps(ret)
        # return ret_str

    def render_obj(self, obj_name, param, lines=None):
        renderer = get_obj_renderer(obj_name)
        return renderer.render(param, lines)

    def render_wiki(self, wiki_source):
        return markdown_to_html(wiki_source)

    def convert_to_html(self, indent_wiki_source):
        regs = []
        lbuf = []
        fbuf = []
        in_func = False
        in_func_indent = 0

        lines = indent_wiki_source.replace("\r", "").split("\n")
        for line in lines + [
            ".",
        ]:
            line2 = line.strip()
            if in_func:
                if line:
                    indent = get_indent(line)
                    if indent > in_func_indent:
                        fbuf.append(line[in_func_indent:])
                    else:
                        in_func = False
                        regs[-1].append(self._render_obj(regs[-1][0], unindent(fbuf)))
                        fbuf = []
                else:
                    fbuf.append("")
            if not in_func:
                if line2.startswith("%"):
                    buf = line2[1:]
                    x = buf.split("#")[0].strip()[-1]
                    if x == ":":
                        in_func = True
                        in_func_indent = get_indent(line)
                        lbuf.append(f"[[[{len(regs)}]]]")
                        regs.append(
                            [
                                line2,
                            ]
                        )
                    else:
                        lbuf.append(f"[[[{len(regs)}]]]")
                        regs.append([line2, self._render_obj(line2, None)])
                else:
                    if line2 != ".":
                        lbuf.append(line)

        if in_func:
            regs[-1].append(self._render_obj(regs[-1][0], unindent(fbuf)))
            fbuf = []

        buf_out = "\n".join(lbuf)
        buf_out = self.render_wiki(buf_out)
        i = 0
        for pos in regs:
            x = f"[[[{i}]]]"
            i += 1
            if x in buf_out:
                buf_out = buf_out.replace(x, pos[1])
        return buf_out


if __name__ == "__main__":

    EXAMPLE = """
# Paragraph

## Section

% block:

% table                     #{"A1":1, "A2": 2}

- test 1
- test 2


% row:
    % col:
        ### header 

        1. Test
        2. Test 2
        3. Test 3
"""

    x = IndentMarkdownProcessor()
    print(x.convert_to_html(EXAMPLE))
