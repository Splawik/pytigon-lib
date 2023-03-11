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

import io
import PIL

from django.core.files.storage import default_storage

from pytigon_lib.schhtml.basehtmltags import (
    BaseHtmlAtomParser,
    register_tag_map,
    ATOM_TAGS,
    PAR_TAGS,
)
from pytigon_lib.schhtml.atom import Atom, NullAtom, BrAtom
from pytigon_lib.schhtml.render_helpers import (
    RenderBackground,
    RenderBorder,
    RenderCellSpacing,
    RenderCellPadding,
    RenderPadding,
    RenderMargin,
    get_size,
)

from pytigon_lib.schtools.images import svg_to_png, spec_resize


class AtomTag(BaseHtmlAtomParser):
    def __init__(self, parent, parser, tag, attrs):
        BaseHtmlAtomParser.__init__(self, parent, parser, tag, attrs)
        self.child_tags = (
            ATOM_TAGS + PAR_TAGS + ["table", "form", "comment", "vimg", "ctr*"]
        )
        self.gparent = parent.gparent

    def draw_atom(self, dc, style, x, y, dx, dy):
        parent = self.parent
        while parent:
            if type(parent) == Atag:
                return parent.draw_atom(dc, style, x, y, dx, dy)
            parent = parent.parent
        return False

    def close(self):
        if self.atom_list:
            self.parent.append_atom_list(self.atom_list)


class BrTag(AtomTag):
    def __init__(self, parent, parser, tag, attrs):
        AtomTag.__init__(self, parent, parser, tag, attrs)

    def close(self):
        self.make_atom_list()
        self.atom_list.append_atom(BrAtom())
        self.parent.append_atom_list(self.atom_list)


class Atag(AtomTag):
    def __init__(self, parent, parser, tag, attrs):
        AtomTag.__init__(self, parent, parser, tag, attrs)
        self.no_wrap = True

    def set_dc_info(self, dc_info):
        ret = AtomTag.set_dc_info(self, dc_info)
        self.make_atom_list()
        return ret

    def append_atom_list(self, atom_list):
        if atom_list:
            for atom in atom_list.atom_list:
                atom.set_parent(self)
                if not atom.is_txt:
                    atom.set_parent(self)
                    if atom.atom_list:
                        for atom2 in atom.atom_list.atom_list:
                            atom2.set_parent(self)
        super().append_atom_list(atom_list)

    def appened_atom(self, atom):
        atom.set_parent(self)
        super().append_atom(atom)

    def draw_atom(self, dc, style, x, y, dx, dy):
        self.reg_action("href", dc.subdc(x, y, dx, dy))
        return False

    def close(self):
        atom = NullAtom()
        self.atom_list.append_atom(atom)
        if len(self.atom_list.atom_list) > 1:
            if not self.atom_list.atom_list[0].data.strip():
                self.atom_list.atom_list = self.atom_list.atom_list[1:]

        for atom in self.atom_list.atom_list:
            if not atom.parent:
                atom.set_parent(self)

        self.parent.append_atom_list(self.atom_list)

    def __repr__(self):
        return "ATag(" + self.tag + ";" + str(self.attrs) + ")"


class ImgDraw(object):
    def __init__(self, img_tag, image, width, height):
        self.img_tag = img_tag
        self.image = image
        self.width = width
        self.height = height

    def draw_atom(self, dc, style, x, y, dx, dy):
        http = self.img_tag.parser.http
        if self.image:
            dc.draw_image(
                x,
                y,
                self.width,
                self.height,
                3,
                self.image,
            )
        else:
            print("null_img")


class ImgTag(AtomTag):
    def __init__(self, parent, parser, tag, attrs):
        AtomTag.__init__(self, parent, parser, tag, attrs)

        if "src" in attrs:
            if "file://" in attrs["src"]:
                self.src = "file://" + default_storage.fs.getsyspath(
                    attrs["src"].replace("file://", "")
                )
            else:
                self.src = attrs["src"]
        else:
            self.src = None
        self.img = None
        self.dx = 0
        self.dy = 0

    def close(self):
        if self.width > 0:
            self.dx = self.width
        if self.height > 0:
            self.dy = self.height

        if self.src:
            http = self.parser.get_http_object()
            try:
                response = http.get(self, self.src)
                if response.ret_code == 404:
                    img = None
                else:
                    img = response.ptr()
                    if type(img) == str:
                        img = img.encode("utf-8")
            except:
                img = None
                print("Image %s not loaded!", self.src)
            if img:
                img_name = self.src.lower()
                if ".png" in img_name:
                    self.img = img
                elif ".svg" in img_name:
                    itype = "simple"
                    if "image-type" in self.attrs:
                        itype = self.attrs["image-type"]
                    if self.width > 0 and self.height > 0:
                        img2 = svg_to_png(img, self.width, self.height, itype)
                        self.img = img2
                    else:
                        self.img = None
                else:
                    try:
                        image = PIL.Image.open(io.BytesIO(img))
                        output = io.BytesIO()
                        image.save(output, "PNG")
                        self.img = output.getvalue()
                    except:
                        pass
            else:
                self.img = None

        if self.img:
            if self.width > 0 and self.height > 0:
                self.dx = self.width
                self.dy = self.height
            else:
                if self.width > 0:
                    (dx, dy) = self.dc_info.get_img_size(self.img)
                    self.dx = self.width
                    self.dy = dy * self.width / dx
                elif self.height > 0:
                    (dx, dy) = self.dc_info.get_img_size(self.img)
                    self.dx = dx * self.height / dy
                    self.dy = self.height
                else:
                    (self.dx, self.dy) = self.dc_info.get_img_size(self.img)

            img_atom = Atom(
                ImgDraw(self, self.img, self.dx, self.dy), self.dx, 0, self.dy, 0
            )
            img_atom.set_parent(self)
            self.make_atom_list()
            self.atom_list.append_atom(img_atom)
            self.parent.append_atom_list(self.atom_list)


class ParCalc(AtomTag):
    def handle_data(self, data):
        parent = self.parent
        while parent:
            if parent.tag == "table":
                table = parent
            if parent.tag == "body":
                body = parent
            if parent.tag == "html":
                html = parent
            parent = parent.parent
        data2 = str(eval(data))
        return AtomTag.handle_data(self, data2)


class HrTag(AtomTag):
    def __init__(self, parent, parser, tag, attrs):
        AtomTag.__init__(self, parent, parser, tag, attrs)
        self.render_helpers = [
            RenderMargin(self),
        ]
        self.extra_space = get_size(self.render_helpers)
        self.in_draw = False

    def close(self):
        b = 1
        if "border" in self.attrs:
            b = int(self.attrs["border"])
        atom = Atom(
            self,
            dx=self.width - self.extra_space[0] - self.extra_space[1],
            dx_space=0,
            dy_up=self.extra_space[2] + b,  # self.height,
            dy_down=self.extra_space[3],
        )

        atom.set_parent(self)
        self.make_atom_list()
        self.atom_list.append_atom(atom)
        self.parent.append_atom_list(self.atom_list)

    def draw_atom(self, dc, style, x, y, dx, dy):
        if self.in_draw:
            return False
        self.in_draw = True
        self.reg_id(dc)
        self.reg_end()
        dc2 = dc.subdc(x, y, dx, dy, True)
        for r in self.render_helpers:
            dc2 = r.render(dc2)
        if "border" in self.attrs:
            dc2.set_line_width(int(self.attrs["border"]))
        dc2.add_line(
            self.extra_space[0],
            self.extra_space[2],
            dx - self.extra_space[0] - self.extra_space[1],
            0,
        )
        dc2.draw()
        self.in_draw = False
        return True


register_tag_map("br", BrTag)
register_tag_map("a", Atag)
register_tag_map("img", ImgTag)
register_tag_map("calc", ParCalc)
register_tag_map("hr", HrTag)
