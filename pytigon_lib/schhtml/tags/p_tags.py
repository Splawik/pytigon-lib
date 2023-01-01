#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

# Pytigon - wxpython and django application framework

# author: "Slawomir Cholaj (slawomir.cholaj@gmail.com)"
# copyright: "Copyright (C) ????/2012 Slawomir Cholaj"
# license: "LGPL 3.0"
# version: "0.1a"

from pytigon_lib.schhtml.basehtmltags import (
    BaseHtmlAtomParser,
    register_tag_map,
    ATOM_TAGS,
    PAR_TAGS,
)
from pytigon_lib.schhtml.render_helpers import (
    RenderBackground,
    RenderBorder,
    RenderCellSpacing,
    RenderCellPadding,
    RenderPadding,
    RenderMargin,
    get_size,
)

from pytigon_lib.schhtml.atom import Atom, BrAtom


LI_INDENT = 20


class InlineElements(BaseHtmlAtomParser):
    def __init__(self, parent, parser, tag, attrs):
        BaseHtmlAtomParser.__init__(self, parent, parser, tag, attrs)
        self.child_tags = (
            ATOM_TAGS + PAR_TAGS + ["table", "form", "comment", "vimg", "ctr*"]
        )
        self.gparent = self
        self.float_width = True
        self.float_height = True
        self.render_helpers = [
            RenderCellSpacing(self),
            RenderMargin(self),
            RenderBorder(self),
            RenderBackground(self),
            RenderCellPadding(self),
            RenderPadding(self),
        ]
        self.extra_space = get_size(self.render_helpers)
        tag = self.tag
        self.tag += ":hover"
        hover_css_attrs = self.parser.css.get_dict(self)
        self.hover_css_attrs = {}
        if hover_css_attrs:
            for key in hover_css_attrs:
                if not (key in self.attrs and self.attrs[key] == hover_css_attrs[key]):
                    self.hover_css_attrs[key] = hover_css_attrs[key]
        self.tag = tag

    def _get_pseudo_margins(self):
        return [
            self.extra_space[0],
            self.extra_space[1],
            self.extra_space[2],
            self.extra_space[3],
        ]

    def calc_width(self):
        if self.atom_list:
            x = self.atom_list.get_width_tab()
        else:
            x = [0, 0, 0]
        ret = [
            x[0] + self.extra_space[0] + self.extra_space[1],
            x[1] + self.extra_space[0] + self.extra_space[1],
            x[2] + self.extra_space[0] + self.extra_space[1],
        ]
        return ret

    def calc_height(self):
        if self.atom_list:
            if not self.atom_list.list_for_draw:
                self.atom_list.gen_list_for_draw(
                    (self.width - self.extra_space[0]) - self.extra_space[1]
                )
            y = self.atom_list.get_height()
        else:
            y = 0

        if y >= 0:
            ret = y + self.extra_space[2] + self.extra_space[3]
        else:
            ret = y
        return ret

    def render(self, dc):
        self.last_rendered_dc = dc
        self.rendered_rects

        self.reg_id(dc)
        if "class" in self.attrs:
            self.reg_action("class", dc)
        self.reg_end()

        dc.annotate("render_tag", {"element": self})

        if dc.handle_html_directly:
            return (0, False)

        if dc.dx == -1:
            dc2 = dc
            dc2.dx = self.width
        else:
            dc2 = dc
        for r in self.render_helpers:
            dc2 = r.render(dc2)

        if self.atom_list:
            if "align" in self.attrs:
                attr = self.attrs["align"]
            else:
                if "text-align" in self.attrs:
                    attr = self.attrs["text-align"]
                else:
                    attr = ""
            if attr == "center":
                align = 1
            else:
                if attr == "right":
                    align = 2
                else:
                    align = 0
            if "valign" in self.attrs:
                attr = self.attrs["valign"]
            else:
                if "vertical-align" in self.attrs:
                    attr = self.attrs["vertical-align"]
                else:
                    attr = ""
            if "top" in attr:
                valign = 0
            else:
                if "bottom" in attr:
                    valign = 2
                else:
                    valign = 1
            if not self.atom_list.list_for_draw:
                self.atom_list.gen_list_for_draw(
                    (self.width - self.extra_space[0]) - self.extra_space[1]
                )

            dy = self.atom_list.draw_atom_list(dc2, align, valign)
        else:
            dy = 0
        return (dy + self.extra_space[2] + self.extra_space[3], False)

    def to_txt(self):
        if self.atom_list:
            return self.atom_list.to_txt()
        else:
            return ""

    def to_attrs(self):
        if self.atom_list:
            attrs = self.atom_list.to_attrs()
        else:
            attrs = {}
        for attr in self.attrs:
            attrs[attr] = self.attrs[attr]
        return attrs

    def to_obj_tab(self):
        if self.atom_list:
            objs = self.atom_list.to_obj_tab()
        else:
            objs = {}
        return objs

    def close(self):
        return BaseHtmlAtomParser.close(self)


class AtomContainer(InlineElements):
    def __init__(self, parent, parser, tag, attrs):
        InlineElements.__init__(self, parent, parser, tag, attrs)

        self.child_tags += [
            "div",
            "p",
            "h1",
            "h2",
            "ctr*",
        ]

        # self.render_helpers = [
        #    RenderMargin(self),
        #    RenderBorder(self),
        #    RenderBackground(self),
        #    RenderPadding(self),
        # ]
        self.extra_space = get_size(self.render_helpers)
        self.draw_txt = ""
        self.in_draw = False

        if type(self.parent).__name__ in ("BodyTag",):
            self.subdiv = False
        else:
            self.subdiv = True

    def _get_pseudo_margins(self):
        return [
            self.extra_space[0],
            self.extra_space[1],
            self.extra_space[2],
            self.extra_space[3],
        ]

    def handle_data(self, data):
        if data.strip() == "":
            return
        else:
            super().handle_data(data)

    def close(self):
        if self.subdiv:
            if not self.width > 0:
                self.width = self.get_width()[2]
            if not self.height > 0:
                self.height = self.get_height()
            else:
                if self.atom_list and not self.atom_list.list_for_draw:
                    self.atom_list.gen_list_for_draw(
                        (self.width - self.extra_space[0]) - self.extra_space[1]
                    )
            atom = Atom(
                self,
                dx=self.width,
                dx_space=0,
                dy_up=self.height,
                dy_down=0,
            )
            atom.set_parent(self)
            _atom_list = self.atom_list
            _rendered_children = self.rendered_children
            self.atom_list = None
            self.make_atom_list()
            self.atom_list.append_atom(atom)
            self.parent.append_atom_list(self.atom_list)
            self.atom_list = _atom_list
            self.rendered_children = _rendered_children

        else:
            BaseHtmlAtomParser.close(self)

    def draw_atom(self, dc, style, x, y, dx, dy):
        if not self.subdiv:
            return
        if self.in_draw:
            return False
        self.in_draw = True
        self.reg_id(dc)
        self.reg_end()
        dc2 = dc.subdc(x, y, dx, dy, True)
        for r in self.render_helpers:
            dc2 = r.render(dc2)
        if self.atom_list:
            self.atom_list.draw_atom_list(dc2)
        self.in_draw = False
        return True

    def child_ready_to_render(self, child):
        if self.subdiv:
            self.make_atom_list()
            # if child.atom_list:
            #    self.atom_list.append_atom_list(child.atom_list)
            # else:
            #    self.atom_list.append_atom(child)

            self.rendered_children.append(child)
        else:
            super().child_ready_to_render(child)


class Par(InlineElements):
    def close(self):
        if (
            issubclass(type(self.parent), Par)
            or issubclass(type(self.parent), AtomContainer)
            or type(self.parent).__name__=='Atag'
        ):
            if self.atom_list:
                self.parent.append_atom_list(self.atom_list)
                if self.tag == "p":
                    self.parent.atom_list.append_atom(BrAtom())
        else:
            return BaseHtmlAtomParser.close(self)


class ParArray(AtomContainer):
    def __init__(self, parent, parser, tag, attrs):
        self.lp = 1
        AtomContainer.__init__(self, parent, parser, tag, attrs)
        self.start = True
        self.end = False

    def get_width(self):
        return self.parent.get_client_width()

    def get_height(self):
        # dy = -1 * self.calc_height()
        dy = 0
        for child in self.rendered_children:
            child.set_width(self.width)
            dyy = child.get_height()
            child.set_height(dyy)
            dy = dy + dyy
        return dy

    def render(self, dc_parm):

        dc_parm.annotate("render_tag", {"element": self})

        if dc_parm.handle_html_directly:
            return (0, False)

        if len(self.rendered_children) > 0:
            child = self.rendered_children[0]
            dc = dc_parm.subdc(
                child.level * LI_INDENT,
                0,
                dc_parm.dx - child.level * LI_INDENT,
                child.height,
            )
            dyy, cont2 = child.render(dc)
            self.rendered_children = self.rendered_children[1:]
            if len(self.rendered_children) > 0:
                cont = True
            else:
                cont = False
            self.start = False
            return (dyy, cont)
        else:
            self.start = False
            return (0, False)

    def draw_atom(self, dc, style, x, y, dx, dy):
        if not self.subdiv:
            return
        if self.in_draw:
            return False
        self.in_draw = True
        self.reg_id(dc)
        self.reg_end()
        dc2 = dc.subdc(x, y, dx, dy, True)
        for r in self.render_helpers:
            dc2 = r.render(dc2)

        cont = True
        self.y = 0
        while cont:
            (dyy, cont) = self.render(
                dc2.subdc(0, self.y, self.get_client_width()[0], dy)
            )
            if dyy > 0:
                self.y += dyy

        # self.render(dc2)
        # if self.atom_list:
        #    self.atom_list.draw_atom_list(dc2)
        self.in_draw = False
        return True

    def close(self):
        self.end = True
        self.parent.make_atom_list()
        # self.parent.atom_list.append_atom(BrAtom())
        super().close()
        # self.parent.child_ready_to_render(self)


class Li(InlineElements):
    def __init__(self, parent, parser, tag, attrs):
        InlineElements.__init__(self, parent, parser, tag, attrs)
        if type(parent) == Ul:
            self.level = parent.level
        else:
            self.level = 0
        self.lp = -1

        self.extra_space[0] += self.level * LI_INDENT

        self.child_tags = (
            ATOM_TAGS + PAR_TAGS + ["table", "form", "comment", "vimg", "ctr*"]
        )

    def child_ready_to_render(self, child):
        self.make_atom_list()
        if child.atom_list:
            self.append_atom_list(child.atom_list)
            if child.tag == "p":
                self.atom_list.append_atom(BrAtom())


class Ul(ParArray):
    def __init__(self, parent, parser, tag, attrs):
        ParArray.__init__(self, parent, parser, tag, attrs)
        self.children = []
        self.level = 1
        p = parent
        while p:
            if type(p) == Ul:
                self.level += 1
            p = p.parent
        self.subdiv = True

    def child_ready_to_render(self, child):
        if self.dc_info.dc.handle_html_directly:
            return super().child_ready_to_render(child)

        if not child in self.children:
            if child.lp < 0:
                child.lp = self.lp
                self.lp += 1
            self.rendered_children.append(child)
            self.children.append(child)
            child.make_atom_list()
            child.atom_list.pre = True
            sym = self._get_sym(child)
            offset = -1 * self.dc_info.get_text_width(sym, self.get_style_id())
            child.atom_list.append_text(sym, self.get_style_id())
            child.atom_list.set_first_line_offset(offset)
            atom = child.atom_list.atom_list[-1]
            del child.atom_list.atom_list[-1]
            child.atom_list.atom_list.insert(0, atom)

            if self.parent.tag == "li" and type(self.parent.parent) == Ul:
                self.parent.parent.child_ready_to_render(self.parent)
                for child in self.rendered_children:
                    self.parent.parent.rendered_children.append(child)
                    self.parent.parent.children.append(child)
                self.rendered_children = []
            # else:
            #    self.parent.child_ready_to_render(self)

    def _get_sym(self, child):
        if self.tag == "c":
            t = "1"
            if "type" in self.attrs:
                t = self.attrs["type"]
            if t == "1":
                return "%3d. " % child.lp
            elif t == "a":
                return "  " + chr(ord("a") + child.lp - 1) + ". "
            elif t == "A":
                return "  " + chr(ord("A") + child.lp - 1) + ". "
            else:
                return "%3d. " % child.lp
        else:
            t = "disc"
            if "type" in self.attrs:
                t = self.attrs["type"]
            if t == "circle":
                z = "●"
            elif t == "square":
                z = "■"
            elif t == "none":
                z = " "
            else:
                z = "•"
                if child.level > 1:
                    z = "○"
            return "  " + z + " "


class Div(AtomContainer):
    pass


class Blockquote(AtomContainer):
    def __init__(self, *argi, **argv):
        super().__init__(*argi, **argv)
        self.subdiv = True


class Pre(Div):
    def __init__(self, *argi, **argv):
        super().__init__(*argi, **argv)
        self.pre = True

    def handle_data(self, data):
        Par.handle_data(self, data)


class H2(Par):
    def close(self, *argi, **argv):
        return super().close(*argi, **argv)


register_tag_map("p", Par)

register_tag_map("h1", Par)
register_tag_map("h2", H2)
register_tag_map("h3", Par)
register_tag_map("h4", Par)
register_tag_map("h5", Par)
register_tag_map("h6", Par)

register_tag_map("blockquote", Blockquote)

register_tag_map("i", Par)
register_tag_map("b", Par)
register_tag_map("s", Par)
register_tag_map("small", Par)
register_tag_map("big", Par)
register_tag_map("sub", Div)
register_tag_map("sup", Div)
register_tag_map("tt", Par)
register_tag_map("span", Par)

register_tag_map("ol", Ul)
register_tag_map("ul", Ul)
register_tag_map("li", Li)

register_tag_map("div", Div)
register_tag_map("pre", Pre)
register_tag_map("code", Pre)
