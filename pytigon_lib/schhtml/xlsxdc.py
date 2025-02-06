import io
import os
import PIL
from decimal import Decimal
from datetime import date, datetime
import xlsxwriter
from pytigon_lib.schhtml.basedc import BaseDc, BaseDcInfo
from pytigon_lib.schfs.vfstools import get_temp_filename


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
        super().__init__(
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
        self.width = width if width >= 0 else -1
        self.height = height if height >= 0 else 1000000000
        self.last_style_tab = None
        self.handle_html_directly = True
        self.temp_file_name = get_temp_filename()
        self.document = xlsxwriter.Workbook(self.temp_file_name)
        self.page_width = width
        self.page_height = height
        self.map_start_tag = {"body": self.body, "div": self.div}
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
            self.notify_callback("start", {"dc": self})

    def close(self):
        if self.notify_callback:
            self.notify_callback("end", {"dc": self})
        self.document.close()
        try:
            with open(self.temp_file_name, "rb") as f_in:
                if self.output_stream:
                    self.output_stream.write(f_in.read())
                elif self.output_name:
                    with open(self.output_name, "wb") as f_out:
                        f_out.write(f_in.read())
        finally:
            os.unlink(self.temp_file_name)

    def annotate(self, what, data):
        element = data.get("element")
        if element and element.parent:
            if what == "start_tag" and element.tag in self.map_start_tag:
                self.map_start_tag[element.tag](element, element.parent)
            elif what == "end_tag" and element.tag in self.map_end_tag:
                self.map_end_tag[element.tag](element, element.parent)

    def _set_width(self, worksheet, col, value):
        width = int(
            value.replace("%", "")
            .replace("px", "")
            .replace("rem", "")
            .replace("em", "")
        )
        worksheet.set_column(col, col, width)

    def _set_height(self, worksheet, row, value):
        if value > 0:
            worksheet.set_row(row, value)

    def _get_color(self, color_str):
        if color_str:
            r, g, b = self.rgbfromhex(color_str)
            return f"#{r:02X}{g:02X}{b:02X}"
        return None

    def _get_style(self, element):
        style_str = self.dc_info.styles[element.style]
        border = int(element.attrs.get("border", 0))
        style_str += f";{border}"
        align = element.attrs.get("align", element.attrs.get("text-align", ""))
        style_str += f";{align}"
        bgcolor = element.attrs.get(
            "bgcolor",
            element.attrs.get("background-color", element.attrs.get("background", "")),
        )
        style_str += f";{bgcolor}"
        brcolor = element.attrs.get("border-color", "")
        style_str += f";{brcolor}"
        fmt = element.attrs.get("format", "")
        style_str += f";{fmt}"

        if style_str not in self.styles_cache:
            style_tab = style_str.split(";")
            fmt = self.document.add_format()
            if style_tab[3] == "1":
                fmt.set_italic()
            if style_tab[4] == "1":
                fmt.set_bold()
            fmt.set_font_name(style_tab[1])
            fmt.set_font_size(
                int(
                    (self.scale * (self.base_font_size * 72) * int(style_tab[2]))
                    / (96 * 100.0)
                )
            )
            fcolor = self._get_color(style_tab[0])
            if fcolor:
                fmt.set_font_color(fcolor)
            fmt.set_border(int(style_tab[6]))
            if style_tab[7] == "center":
                fmt.set_align("center")
            elif style_tab[7] == "right":
                fmt.set_align("right")
            else:
                fmt.set_align("left")
            bgcolor = self._get_color(style_tab[8])
            if bgcolor:
                fmt.set_bg_color(bgcolor)
            brcolor = self._get_color(style_tab[9])
            if brcolor:
                fmt.set_border_color(brcolor)
            if style_tab[10]:
                fmt.set_num_format(style_tab[10])
            self.styles_cache[style_str] = fmt
        return self.styles_cache[style_str]

    def _process_atom_list(self, element):
        return (
            "".join(
                atom.data
                for atom in element.atom_list.atom_list
                if isinstance(atom.data, str)
            )
            if element.atom_list and element.atom_list.atom_list
            else ""
        )

    def body(self, element, parent):
        if not hasattr(element, "worksheet"):
            title = element.attrs.get("title", "")
            element.worksheet = self.document.add_worksheet(title)
            element.status = [0, 0]
        if "cellwidth" in element.attrs:
            for col, value in enumerate(element.attrs["cellwidth"].split(";")):
                self._set_width(element.worksheet, col, value)

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
        td_class = element.attrs.get("class", "")
        row, col = parent.parent.parent.status[0], parent.parent.parent.status[1]

        if td_class in ("int", "float", "decimal"):
            num = (
                int(txt)
                if td_class == "int"
                else float(txt) if td_class == "float" else Decimal(txt)
            )
            parent.parent.parent.worksheet.write_number(row, col, num, style)
        elif td_class in ("date", "datetime"):
            d = (
                date.fromisoformat(txt)
                if td_class == "date"
                else datetime.fromisoformat(txt)
            )
            parent.parent.parent.worksheet.write_datetime(row, col, d, style)
        elif td_class == "bool":
            b = txt.strip() not in ("", "0", "False", "None")
            parent.parent.parent.worksheet.write_boolean(row, col, b, style)
        elif td_class == "formula":
            parent.parent.parent.worksheet.write_formula(row, col, txt, style)
        elif td_class == "url":
            parent.parent.parent.worksheet.write_url(row, col, txt, style)
        else:
            parent.parent.parent.worksheet.write(row, col, txt, style)

        self._set_height(parent.parent.parent.worksheet, row, style.font_size + 4)
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
        self.h(element, parent, 0)

    def h2(self, element, parent):
        self.h(element, parent, 1)

    def h3(self, element, parent):
        self.h(element, parent, 2)

    def h4(self, element, parent):
        self.h(element, parent, 3)

    def h5(self, element, parent):
        self.h(element, parent, 4)

    def h6(self, element, parent):
        self.h(element, parent, 5)


class XlsxDcinfo(BaseDcInfo):
    def __init__(self, dc):
        super().__init__(dc)

    def get_text_height(self, word, style):
        return 1

    def get_img_size(self, png_data):
        try:
            png_stream = io.BytesIO(png_data)
            image = PIL.Image.open(png_stream)
            return image.size if image else (0, 0)
        except Exception:
            return (0, 0)
