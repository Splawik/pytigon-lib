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

from pytigon_lib.schtools.images import svg_to_png, spec_resize
from django.core.files.storage import default_storage

import PIL


class RenderBase(object):
    def __init__(self, parent):
        self.parent = parent
        self.rendered_attribs = None

    def get_size(self):
        if self.rendered_attribs:
            for attr in self.rendered_attribs:
                if attr in self.parent.attrs:
                    if hasattr(self, "handle_get_size"):
                        return self.handle_get_size(self.parent.attrs[attr])
                    else:
                        return [0, 0, 0, 0]
        return [0, 0, 0, 0]

    def render(self, dc):
        if self.rendered_attribs:
            for attr in self.rendered_attribs:
                value = None
                if attr in self.parent.attrs:
                    value = self.parent.attrs[attr]
                if self.parent.hover and attr in self.parent.hover_css_attrs:
                    value = self.parent.hover_css_attrs[attr]
                if value:
                    return self.handle_render(dc, attr, value)
        return dc


class RenderBackground(RenderBase):
    def __init__(self, parent):
        RenderBase.__init__(self, parent)
        self.rendered_attribs = (
            "bgcolor",
            "background-color",
            "background-image",
            "background",
        )

    def background(self, dc, bgcolor, image_url, repeat, attachment, x, y):
        # if dc.calc_only:
        #    return
        if bgcolor:
            (r, g, b) = dc.rgbfromhex(bgcolor)
            dc.set_color(r, g, b)
            dc.add_rectangle(0, 0, dc.dx, dc.dy)
            dc.fill()
        if image_url:
            style = 0
            if "background-size" in self.parent.attrs:
                attr = self.parent.attrs["background-size"]
                if attr == "cover":
                    style = 2
                elif attr == "contain":
                    style = 3
                elif "100%" in attr:
                    style = 1
            if repeat:
                if repeat == "repeat-x":
                    style = 4
                elif repeat == "repeat-y":
                    style = 5
                elif repeat == "no-repeat":
                    pass
                else:
                    style = 6

            try:
                http = self.parent.parser.get_http_object()
                response = http.get(self, image_url)

                if response.ret_code == 404:
                    img = None
                else:
                    img = response.ptr()
                    if type(img) == str:
                        img = img.encode("utf-8")
            except:
                img = None

            if img:
                img_name = image_url.lower()
                if ".png" in img_name:
                    img_bytes = img
                elif ".svg" in img_name:
                    itype = "simple"
                    if "image-type" in self.parent.attrs:
                        itype = self.parent.attrs["image-type"]
                    img2 = svg_to_png(img, int(dc.dx), int(dc.dy), itype)
                    img_bytes = img2
                else:
                    image = PIL.Image.open(io.BytesIO(img))
                    output = io.BytesIO()
                    image.save(output, "PNG")
                    img_bytes = output.getvalue()

                dc.draw_image(0, 0, dc.dx, dc.dy, style, img_bytes)
                # dc.draw_image(0, 0, dc.dx, dc.dy, 3, img_bytes)

    def handle_render(self, dc, attr_name, value):
        if attr_name == "background-image":
            img_url = value.replace("url(", "").replace(")", "")
            self.background(dc, None, img_url, None, None, None, None)
        elif attr_name == "background":
            tab_attr = value.split(" ")
            attr_nr = 0
            background_color = "#ffffff"
            background_image = ""
            background_repeat = ""
            background_attachment = ""
            background_position_x = ""
            background_position_y = ""
            for pos in tab_attr:
                if attr_nr == 0:  # bgcolor
                    if "#" in pos:
                        background_color = pos
                        attr_nr += 1
                        continue
                    attr_nr += 1
                if attr_nr == 1:  # url(image)
                    if "url" in pos:
                        background_image = pos
                        attr_nr += 1
                        continue
                    attr_nr += 1
                if attr_nr == 2:
                    if "repeat" in pos:
                        background_repeat = pos
                        attr_nr += 1
                        continue
                    attr_nr += 1
                if attr_nr == 3:
                    if pos in ("scroll", "fixed", "inherit"):
                        background_attachment = pos
                        attr_nr += 1
                        continue
                    attr_nr += 1
                if attr_nr == 4:
                    if pos in ("left", "center", "right"):
                        background_position_x = pos
                        attr_nr += 1
                        continue
                    attr_nr += 1
                if attr_nr == 5:
                    if pos in ("top", "center", "bottom"):
                        background_position_y = pos
                        attr_nr += 1
                        continue
                    attr_nr += 1
                break
            self.background(
                dc,
                background_color,
                background_image,
                background_repeat,
                background_attachment,
                background_position_x,
                background_position_y,
            )
        else:
            if "#" in value:
                self.background(dc, value, None, None, None, None, None)
        return dc


class RenderBorder(RenderBase):
    def __init__(self, parent):
        RenderBase.__init__(self, parent)
        self.rendered_attribs = (
            "border-top",
            "border-right",
            "border-bottom",
            "border-left",
            "border",
        )

    def handle_get_size(self, border):
        return sizes_from_attr(border, self)

    def handle_render(self, dc, attr_name, border):
        p = self.handle_get_size(border)
        b = p[0]
        if b > 0:
            if "border-color" in self.parent.attrs:
                (_r, _g, _b) = dc.rgbfromhex(self.parent.attrs["border-color"])
                dc.set_color(_r, _g, _b, 255)
            else:
                dc.set_color(0, 0, 0, 255)
            dc.set_line_width(b)
            test = False
            if "border-top" in self.parent.attrs:
                dc.add_line(b / 2, b / 2, dc.dx - b, 0)
                test = True
            if "border-right" in self.parent.attrs:
                dc.add_line(dc.dx - b / 2, b / 2, 0, dc.dy - b)
                test = True
            if "border-bottom" in self.parent.attrs:
                dc.add_line(b / 2, dc.dy - b / 2, dc.dx - b, 0)
                test = True
            if "border-left" in self.parent.attrs:
                dc.add_line(b / 2, b / 2, 0, dc.dy - b)
                test = True
            if not test:
                dc.add_rectangle(b / 2, b / 2, dc.dx - b, dc.dy - b)
            dc.draw()
        return dc.subdc(b, b, dc.dx - 2 * b, dc.dy - 2 * b)


class RenderPaddingMargin(RenderBase):
    def __init__(self, parent):
        RenderBase.__init__(self, parent)

    def handle_get_size(self, padding):
        return sizes_from_attr(padding, self)

    def handle_render(
        self,
        dc,
        attr_name,
        padding,
    ):
        p = self.handle_get_size(padding)
        return dc.subdc(p[0], p[2], (dc.dx - p[0]) - p[1], (dc.dy - p[2]) - p[3])


class RenderCellPadding(RenderPaddingMargin):
    def __init__(self, parent):
        RenderPaddingMargin.__init__(self, parent)
        self.rendered_attribs = ("cellpadding",)


class RenderCellSpacing(RenderPaddingMargin):
    def __init__(self, parent):
        RenderPaddingMargin.__init__(self, parent)
        self.rendered_attribs = ("cellspacing",)


class RenderPadding(RenderPaddingMargin):
    def __init__(self, parent):
        RenderPaddingMargin.__init__(self, parent)
        self.rendered_attribs = ("padding",)


class RenderMargin(RenderPaddingMargin):
    def __init__(self, parent):
        RenderPaddingMargin.__init__(self, parent)
        self.rendered_attribs = ("margin",)


def sizes_from_attr(attr_value, parent):
    if type(attr_value) == str:
        sizes = attr_value.strip().replace("px", "").replace("em", "").split(" ")
        norm_sizes = []
        for i, size in enumerate(sizes):
            if size.endswith("%"):
                try:
                    x = int(size[:-1])
                    if (
                        (len(sizes) == 4 and i in (1, 3))
                        or (len(sizes) == 2 and i == 1)
                        or len(sizes) == 1
                    ):
                        p = parent.parent
                        while p != None and p.width <= 0:
                            p = p.parent
                        if p:
                            norm_sizes.append(int(p.width * x / 100))
                        else:
                            norm_sizes.append(10)
                    else:
                        p = parent
                        while p and p.height <= 0:
                            p = p.parent
                        if p:
                            norm_sizes.append(int(p.width * x / 100))
                        else:
                            norm_sizes.append(10)
                except:
                    norm_sizes.append(10)
            else:
                try:
                    x = int(size)
                    norm_sizes.append(x)
                except:
                    norm_sizes.append(10)
        p = [10, 10, 10, 10]
        if len(sizes) == 1:
            p = [norm_sizes[0], norm_sizes[0], norm_sizes[0], norm_sizes[0]]
        elif len(sizes) == 2:
            p[2] = p[3] = norm_sizes[0]
            p[0] = p[1] = norm_sizes[1]
        elif len(sizes) == 4:
            p[0] = norm_sizes[3]
            p[1] = norm_sizes[1]
            p[2] = norm_sizes[0]
            p[3] = norm_sizes[2]
        else:
            print(
                "size_from_attr error:",
                "{" + attr_value + "}",
                len(sizes),
                sizes,
            )
        return p
    else:
        return attr_value


def get_size(render_list):
    s = [0, 0, 0, 0]
    for pos in render_list:
        size = pos.get_size()
        s[0] += size[0]
        s[1] += size[1]
        s[2] += size[2]
        s[3] += size[3]
    return s
