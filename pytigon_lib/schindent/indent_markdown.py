import json
from re import template
import markdown
from django.template.loader import select_template

REG_OBJ_RENDERER = {}


class BaseObjRenderer:
    def __init__(self, extra_info=""):
        self.extra_info = extra_info
        self.line_number = 0

    def _get_line_number(self, parent_processor):
        if self.line_number == 0:
            self.line_number = 0
            parent = parent_processor
            if parent.line_number < 0:
                return -1
            while parent:
                self.line_number += parent.line_number
                parent = parent.parent_processor
        return self.line_number

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

    def gen_context(self, param, lines, output_format, parent_processor):
        return {}

    def get_renderer_template_name(self):
        return None

    def get_edit_template_name(self):
        return "schwiki/wikiobj_edit.html"

    def edit_on_page_link(self, parent_processor, right=False):
        buf = ""
        line_number = self._get_line_number(parent_processor)
        title = self.get_info()["title"]
        if line_number < 0:
            return ""
        if right:
            buf = " wiki-object-edit-right"
        return """
            {%% if perms.wiki.add_page %%}
                <a class="wiki-object-edit%s" href="{{base_path}}schwiki/edit_object_on_page/{{object.id}}/%d/?name={{name}}&only_content=1" target="popup_edit" title="%s properties">
                    %s <span class="fa fa-cog fa-2" />
                </a>
            {%% endif %%}
        """ % (
            buf,
            line_number,
            title,
            title,
        )

    def render(self, param, lines, output_format, parent_processor):
        template_name = self.get_renderer_template_name()
        context = self.gen_context(param, lines, output_format, parent_processor)
        context["output_format"] = output_format
        context["line_number"] = self._get_line_number(parent_processor)

        if template_name:
            t = select_template(
                [
                    template_name,
                ]
            )
            ret = t.render(context)
            return (
                ret.replace("[%", "{%")
                .replace("%]", "%}")
                .replace("[{", "{{")
                .replace("}]", "}}")
            )
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
    def __init__(
        self, output_format="html", parent_processor=None, uri=None, line_number=0
    ):
        self.output_format = output_format
        self.parent_processor = parent_processor
        self.named_renderers = {}
        self.uri = uri
        self.lines = None
        self.line_number = line_number

    def get_root(self):
        if self.parent_processor:
            return self.parent_processor.get_root()
        return self

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

        if "name/" in obj_name:
            if lines:
                name = obj_name.split("name/")[1].strip()
                self.named_renderers[name] = lines[0].strip()
            return ""

        if obj_name in self.named_renderers:
            buf = self.line_number
            self.line_number = -1
            ret = self._render_obj(self.named_renderers[obj_name], lines)
            self.line_number = buf
            return ret

        return self.render_obj(obj_name, param, lines)

    def render_obj(self, obj_name, param, lines=None):
        renderer = get_obj_renderer(obj_name)
        return renderer.render(param, lines, self.output_format, self)

    def render_wiki(self, wiki_source):
        return markdown_to_html(wiki_source)

    def convert(self, indent_wiki_source):
        regs = []
        lbuf = []
        fbuf = []
        in_func = False
        in_func_indent = 0
        root = self.get_root()
        self.lines = indent_wiki_source.replace("\r", "").split("\n")
        for line in self.lines + [
            ".",
        ]:
            self.line_number += 1
            # root.line_number += 1
            line2 = line.strip()
            if in_func:
                if line:
                    indent = get_indent(line)
                    if indent > in_func_indent:
                        fbuf.append(line[in_func_indent:])
                    else:
                        in_func = False
                        tmp = self.line_number
                        self.line_number -= len(fbuf) + 1
                        regs[-1].append(self._render_obj(regs[-1][0], unindent(fbuf)))
                        self.line_number = tmp
                        fbuf = []
                else:
                    fbuf.append("")

            if not in_func:

                #                self.line_number += 1
                #                parent = self.parent_processor
                #                while parent:
                #                   parent.line_number += 1
                #                    parent = parent.parent_processor

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
            tmp = self.line_number
            self.line_number -= len(fbuf) + 1
            regs[-1].append(self._render_obj(regs[-1][0], unindent(fbuf)))
            self.line_number = tmp
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


def imd2html(buf):
    x = IndentMarkdownProcessor(output_format="html")
    return x.convert(buf)


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
