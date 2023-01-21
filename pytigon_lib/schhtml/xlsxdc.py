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
import os
import PIL
from decimal import Decimal
from datetime import date, datetime

from pytigon_lib.schhtml.basedc import BaseDc, BaseDcInfo
from pytigon_lib.schfs.vfstools import get_temp_filename

import xlsxwriter


class XlsxDc(BaseDc):
    def __init__(
        self,
        ctx=None,
        calc_only=False,
        width=8.5,
        height=11,
        output_name=None,
        output_stream=None,
        scale=1.0,
        notify_callback=None,
        record=False,
    ):
        BaseDc.__init__(
            self,
            calc_only,
            -1,
            -1,
            output_name,
            output_stream,
            scale,
            notify_callback,
            record,
        )
        self.dc_info = XlsxDcinfo(self)
        self.type = None

        if width < 0:
            self.width = -1
        if height < 0:
            self.height = 1000000000

        self.last_style_tab = None
        self.handle_html_directly = True
        self.temp_file_name = get_temp_filename()
        self.document = xlsxwriter.Workbook(self.temp_file_name)

        self.page_width = width
        self.page_height = height

        self.map_start_tag = {
            "body": self.body,
            "div": self.div,
        }

        self.map_end_tag = {
            "tr": self.tr,
            "td": self.td,
            "th": self.th,
            "h1": self.h1,
            "h2": self.h2,
            "h3": self.h3,
            "h4": self.h4,
            "h5": self.h5,
            "h6": self.h6,
            "p": self.p,
            "img": self.image,
            "body": self.end_body,
        }

        self.last_ = None
        self.styles_cache = {}

        if self.notify_callback:
            self.notify_callback(
                "start",
                {"dc": self},
            )

    def close(self):
        if self.notify_callback:
            self.notify_callback(
                "end",
                {"dc": self},
            )
        self.document.close()
        with open(self.temp_file_name, "rb") as f_in:
            if self.output_stream:
                self.output_stream.write(f_in.read())
            elif self.output_name:
                with open(self.output_name, "wb") as f_out:
                    f_out.write(f_in.read())
        os.unlink(self.temp_file_name)

    def annotate(self, what, data):
        if what == "start_tag":
            element = data["element"]
            if element:
                parent = element.parent
                if element and parent:
                    if element.tag in self.map_start_tag:
                        self.map_start_tag[element.tag](element, parent)
        elif what == "end_tag":
            element = data["element"]
            if element:
                parent = element.parent
                if element and parent:
                    if element.tag in self.map_end_tag:
                        self.map_end_tag[element.tag](element, parent)

    def _set_width(self, worksheet, col, value):
        if "%" in value:
            width = int(value.replace("%", ""))
        else:
            width = int(value.replace("px", "").replace("rem", "").replace("em", ""))
        worksheet.set_column(col, col, width)

    def _set_height(self, worksheet, row, value):
        if value == 0:
            worksheet.set_row(row, 0)
        else:
            if len(worksheet.row_sizes) >= row + 1:
                cur_height = worksheet.row_sizes[row]
            else:
                cur_height = worksheet.default_row_height

            if cur_height < value:
                worksheet.set_row(row, value)

    def _get_color(self, color_str):
        if color_str:
            (r, g, b) = self.rgbfromhex(color_str)
            return "#%02X%02X%02X" % (r, g, b)
        else:
            return None

    def _get_style(self, element):
        style_str = self.dc_info.styles[element.style]
        if "border" in element.attrs:
            if int(element.attrs["border"]) > 1:
                style_str += ";2"
            else:
                style_str += ";1"
        else:
            style_str += ";0"

        if "align" in element.attrs:
            attr = element.attrs["align"]
        else:
            if "text-align" in element.attrs:
                attr = element.attrs["text-align"]
            else:
                attr = ""
        style_str += ";" + attr

        bgcolor = ""
        if "bgcolor" in element.attrs:
            bgcolor = element.attrs["bgcolor"]
        elif "background-color" in element.attrs:
            bgcolor = element.attrs["background-color"]
        elif "background" in element.attrs:
            bgcolor = element.attrs["background"]
        style_str += ";" + bgcolor

        if "border-color" in element.attrs:
            brcolor = element.attrs["border-color"]
        else:
            brcolor = ""
        style_str += ";" + brcolor

        if "format" in element.attrs:
            f = element.attrs["format"]
        else:
            f = ""
        style_str += ";" + f

        if not style_str in self.styles_cache:
            style_tab = style_str.split(";")
            format = self.document.add_format()

            if style_tab[3] == "1":
                format.set_italic()
            if style_tab[4] == "1":
                format.set_bold()
            format.set_font_name(style_tab[1])
            format.set_font_size(
                int(
                    (self.scale * (self.base_font_size * 72) * int(style_tab[2]))
                    / (96 * 100.0)
                )
            )

            fcolor = self._get_color(style_tab[0])
            if fcolor:
                format.set_font_color(fcolor)

            format.set_border(int(style_tab[6]))

            if style_tab[7] == "center":
                format.set_align("center")
            else:
                if style_tab[7] == "right":
                    format.set_align("right")
                else:
                    format.set_align("left")

            bgcolor = self._get_color(style_tab[8])
            if bgcolor:
                format.set_bg_color(bgcolor)

            brcolor = self._get_color(style_tab[9])
            if brcolor:
                format.set_border_color(brcolor)

            f = style_tab[10]
            if f:
                format.set_num_format(f)

            self.styles_cache[style_str] = format

        return self.styles_cache[style_str]

    def _process_atom_list(self, element):
        ret = ""
        if element.atom_list and element.atom_list.atom_list:
            for atom in element.atom_list.atom_list:
                if type(atom.data) == str:
                    ret += atom.data
        return ret

    def body(self, element, parent):
        if not hasattr(element, "worksheet"):
            if "title" in element.attrs:
                element.worksheet = self.document.add_worksheet(element.attrs["title"])
            else:
                element.worksheet = self.document.add_worksheet()
            element.status = [0, 0]
        if "cellwidth" in element.attrs:
            for col, value in enumerate(element.attrs["cellwidth"].split(";")):
                self._set_width(
                    element.worksheet,
                    col,
                    value,
                )

    def end_body(self, element, parent):
        if self.notify_callback:
            self.notify_callback(
                "worksheet",
                {"dc": self, "worksheet": element.worksheet, "status": element.status},
            )

    def div(self, element, parent):
        if parent.tag == "body":
            element.worksheet = parent.worksheet
            element.status = parent.status

    def tr(self, element, parent):
        parent.parent.status[0] += 1
        parent.parent.status[1] -= len(element.td_list)

    def td(self, element, parent):
        style = self._get_style(element)
        txt = self._process_atom_list(element)
        td_class = ""
        if "class" in element.attrs:
            td_class = element.attrs["class"]

        if td_class in ("int", "float", "decimal"):
            if td_class == "int":
                num = int(txt)
            elif td_class == "float":
                num = float(txt)
            elif td_class == "decimal":
                num = Decimal(txt)
            parent.parent.parent.worksheet.write_number(
                parent.parent.parent.status[0],
                parent.parent.parent.status[1],
                num,
                style,
            )
        elif td_class in ("date", "datetime"):
            if td_class == "date":
                d = date.fromisoformat(txt)
            else:
                d = datetime.fromisoformat(txt)
            parent.parent.parent.worksheet.write_datetime(
                parent.parent.parent.status[0], parent.parent.parent.status[1], d, style
            )
        elif td_class in ("bool",):
            txt2 = txt.strip()
            if (not txt2) or txt2 == "0" or txt2 == "False" or txt2 == "None":
                b = False
            else:
                b = True
            parent.parent.parent.worksheet.write_boolean(
                parent.parent.parent.status[0], parent.parent.parent.status[1], b, style
            )
        elif td_class in ("formula",):
            parent.parent.parent.worksheet.write_formula(
                parent.parent.parent.status[0],
                parent.parent.parent.status[1],
                txt,
                style,
            )
        elif td_class in ("url",):
            parent.parent.parent.worksheet.write_url(
                parent.parent.parent.status[0],
                parent.parent.parent.status[1],
                txt,
                style,
            )
        else:  # "", "str"
            parent.parent.parent.worksheet.write(
                parent.parent.parent.status[0],
                parent.parent.parent.status[1],
                txt,
                style,
            )

        self._set_height(
            parent.parent.parent.worksheet,
            parent.parent.parent.status[0],
            style.font_size + 4,
        )

        parent.parent.parent.status[1] += 1
        parent.td_list.append(self)

    def th(self, element, parent):
        if "width" in element.attrs:
            self._set_width(
                parent.parent.parent.worksheet,
                parent.parent.parent.status[1],
                element.attrs["width"],
            )
        self.td(element, parent)

    def h(self, element, parent, level):
        if hasattr(parent, "worksheet"):
            style = self._get_style(element)
            txt = self._process_atom_list(element)

            parent.worksheet.write(parent.status[0], parent.status[1], txt, style)

            self._set_height(parent.worksheet, parent.status[0], style.font_size + 4)

            parent.status[0] += 1

    def p(self, element, parent):
        if parent.tag == "body":
            style = self._get_style(element)
            txt = self._process_atom_list(element)

            parent.worksheet.write(parent.status[0], parent.status[1], txt, style)
            self._set_height(parent.worksheet, parent.status[0], style.font_size + 4)

            parent.status[0] += 1

    def image(self, element, parent):
        if element.img and parent.tag in ("body", "div"):
            img_stream = io.BytesIO(element.img)
            parent.worksheet.insert_image(
                parent.status[0],
                parent.status[1],
                "https://pytigon.eu/pytigon.png",
                {"image_data": img_stream},
            )

            w, h = self.dc_info.get_img_size(element.img)
            self._set_height(parent.worksheet, parent.status[0], h)
            parent.status[0] += 1

    def h1(self, element, parent):
        return self.h(element, parent, 0)

    def h2(self, element, parent):
        return self.h(element, parent, 1)

    def h3(self, element, parent):
        return self.h(element, parent, 2)

    def h4(self, element, parent):
        return self.h(element, parent, 3)

    def h5(self, element, parent):
        return self.h(element, parent, 4)

    def h6(self, element, parent):
        return self.h(element, parent, 5)


class XlsxDcinfo(BaseDcInfo):
    def __init__(self, dc):
        BaseDcInfo.__init__(self, dc)

    def get_test_height(self, word, style):
        return 1

    def get_img_size(self, png_data):
        try:
            png_stream = io.BytesIO(png_data)
            image = PIL.Image.open(png_stream)
        except:
            image = None
        if image:
            w, h = image.size
            return (w, h)
        else:
            return (0, 0)
