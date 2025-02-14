import io
from math import pi
import cairo

from pytigon_lib.schhtml.basedc import BaseDc, BaseDcInfo


class CairoDc(BaseDc):
    def __init__(
        self,
        ctx=None,
        calc_only=False,
        width=-1,
        height=-1,
        output_name=None,
        output_stream=None,
        scale=1.0,
        notify_callback=None,
        record=False,
    ):
        super().__init__(
            calc_only,
            width,
            height,
            output_name,
            output_stream,
            scale,
            notify_callback,
            record,
        )
        self.width = width if width >= 0 else self.default_width
        self.height = height if height >= 0 else self.default_height
        self.dc_info = CairoDcInfo(self)
        self.type = None
        self.last_style_tab = None
        self.last_move_to = None

        if self.calc_only:
            self.surf = cairo.ImageSurface(cairo.FORMAT_RGB24, 10, 10)
            self.ctx = cairo.Context(self.surf)
        else:
            if ctx:
                self.surf = None
                self.ctx = ctx
            else:
                self._initialize_surface(output_name, output_stream)
            self.ctx.set_line_cap(cairo.LINE_CAP_ROUND)

    def _initialize_surface(self, output_name, output_stream):
        if output_name:
            name = output_name.lower()
            if ".pdf" in name:
                self.surf = cairo.PDFSurface(
                    output_stream or output_name, self.width, self.height
                )
                self.type = "pdf"
            elif ".svg" in name:
                self.surf = cairo.SVGSurface(
                    output_stream or output_name, self.width, self.height
                )
                self.type = "svg"
            elif ".png" in name:
                self.surf = cairo.ImageSurface(
                    cairo.FORMAT_RGB24, self.width, self.height
                )
                self.type = "png"
            else:
                self.surf = cairo.ImageSurface(
                    cairo.FORMAT_RGB24, self.width, self.height
                )
        else:
            self.surf = cairo.ImageSurface(cairo.FORMAT_RGB24, self.width, self.height)
        self.ctx = cairo.Context(self.surf)

    def close(self):
        if not self.calc_only and self.surf:
            if self.type in ("svg", "pdf"):
                self.ctx.show_page()
            self.surf.finish()

    def _move_to(self, x, y):
        self.ctx.move_to(x * self.scale, y * self.scale)
        self.last_move_to = (x * self.scale, y * self.scale)

    def start_page(self):
        self.ctx.show_page()
        super().start_page()

    def draw(self, preserve=False):
        self.ctx.stroke_preserve() if preserve else self.ctx.stroke()
        super().draw(preserve)

    def fill(self, preserve=False):
        self.ctx.fill_preserve() if preserve else self.ctx.fill()
        super().fill()

    def set_color(self, r, g, b, a=255):
        self.ctx.set_source_rgb(r / 256.0, g / 256.0, b / 256.0)
        super().set_color(r, g, b, a)

    def set_line_width(self, width):
        self.ctx.set_line_width(width * self.scale)
        super().set_line_width(width)

    def set_style(self, style):
        if style == self.last_style:
            return self.last_style_tab
        style_tab = self.dc_info.styles[style].split(";")
        self.last_style_tab = style_tab
        slant = (
            cairo.FONT_SLANT_ITALIC if style_tab[3] == "1" else cairo.FONT_SLANT_NORMAL
        )
        weight = (
            cairo.FONT_WEIGHT_BOLD if style_tab[4] == "1" else cairo.FONT_WEIGHT_NORMAL
        )
        self.ctx.select_font_face(style_tab[1], slant, weight)
        r, g, b = self.rgbfromhex(style_tab[0])
        self.ctx.set_font_size(
            (self.scale * self.base_font_size * int(style_tab[2])) / 100
        )
        self.ctx.set_source_rgb(r / 256.0, g / 256.0, b / 256.0)
        super().set_style(style)
        return style_tab

    def add_line(self, x, y, dx, dy):
        self._move_to(x, y)
        self.ctx.line_to((x + dx) * self.scale, (y + dy) * self.scale)
        self.last_move_to = ((x + dx) * self.scale, (y + dy) * self.scale)
        super().add_line(x, y, dx, dy)

    def add_rectangle(self, x, y, dx, dy):
        self.ctx.rectangle(
            x * self.scale, y * self.scale, dx * self.scale, dy * self.scale
        )
        super().add_rectangle(x, y, dx, dy)

    def add_rounded_rectangle(self, x, y, dx, dy, radius):
        degrees = pi / 180.0
        self.ctx.new_sub_path()
        self.ctx.arc(
            (x + dx - radius) * self.scale,
            (y + radius) * self.scale,
            radius * self.scale,
            -90 * degrees,
            0 * degrees,
        )
        self.ctx.arc(
            (x + dx - radius) * self.scale,
            (y + dy - radius) * self.scale,
            radius * self.scale,
            0 * degrees,
            90 * degrees,
        )
        self.ctx.arc(
            (x + radius) * self.scale,
            (y + dy - radius) * self.scale,
            radius * self.scale,
            90 * degrees,
            180 * degrees,
        )
        self.ctx.arc(
            (x + radius) * self.scale,
            (y + radius) * self.scale,
            radius * self.scale,
            180 * degrees,
            270 * degrees,
        )
        self.ctx.close_path()
        super().add_rounded_rectangle(x, y, dx, dy, radius)

    def add_arc(self, x, y, radius, angle1, angle2):
        self.ctx.arc(
            x * self.scale,
            y * self.scale,
            radius * self.scale,
            (2 * pi * angle1) / 360,
            (2 * pi * angle2) / 360,
        )
        super().add_arc(x, y, radius, angle1, angle2)

    def add_ellipse(self, x, y, dx, dy):
        self.ctx.save()
        self.ctx.translate((x + dx / 2) * self.scale, (y + dy / 2) * self.scale)
        self.ctx.scale(self.scale * dx / 2.0, self.scale * dy / 2.0)
        self.ctx.arc(0.0, 0.0, 1.0, 0.0, 2.0 * pi)
        self.ctx.restore()
        super().add_ellipse(x, y, dx, dy)

    def add_polygon(self, xytab):
        pos0 = xytab[0]
        self.ctx.move_to(pos0[0] * self.scale, pos0[1] * self.scale)
        for pos in xytab[1:]:
            self.ctx.line_to(pos[0] * self.scale, pos[1] * self.scale)
        self.ctx.close_path()
        self.last_move_to = [pos[0] * self.scale, pos[1] * self.scale]
        super().add_polygon(xytab)

    def add_spline(self, xytab, close):
        pos0 = xytab[0]
        self.ctx.move_to(pos0[0], pos0[1])
        for pos in xytab[1:]:
            self.ctx.line_to(pos[0], pos[1])
            self.last_move_to = pos
        if close:
            self.ctx.close_path()
            self.last_move_to = pos0
        super().add_spline(xytab, close)

    def draw_text(self, x, y, txt):
        sizes = self.ctx.text_extents(txt)[:4]
        self.ctx.move_to((x - sizes[0] / 2) * self.scale, y * self.scale)
        self.ctx.show_text(txt)
        super().draw_text(x, y, txt)

    def draw_rotated_text(self, x, y, txt, angle):
        self.ctx.save()
        self.ctx.move_to(x * self.scale, y * self.scale)
        self.ctx.rotate((2 * pi * angle) / 360)
        self.ctx.show_text(txt)
        self.ctx.restore()
        super().draw_rotated_text(x, y, txt, angle)

    def draw_image(self, x, y, dx, dy, scale, png_data):
        try:
            png_stream = io.BytesIO(png_data)
            surface = cairo.ImageSurface.create_from_png(png_stream)
        except Exception:
            surface = cairo.ImageSurface.create_from_png("sleeptimer.png")
        w = surface.get_width()
        h = surface.get_height()
        self.ctx.save()
        self.ctx.rectangle(x, y, dx, dy)
        self.ctx.clip()
        x_scale, y_scale = self._scale_image(x, y, dx, dy, scale, w, h)
        if scale < 4:
            self.ctx.scale(x_scale, y_scale)
            self.ctx.set_source_surface(surface, x / x_scale, y / y_scale)
            self.ctx.paint()
        else:
            delta_x = 0
            delta_y = 0
            while delta_y < dy:
                if scale == 4 and delta_y > 0:
                    break
                delta_x = 0
                while delta_x < dx:
                    if scale == 5 and delta_x > 0:
                        break
                    self.ctx.set_source_surface(surface, x + delta_x, y + delta_y)
                    self.ctx.paint()
                    delta_x += w
                delta_y += h
        self.ctx.restore()
        super().draw_image(x, y, dx, dy, scale, png_data)


class CairoDcInfo(BaseDcInfo):
    def __init__(self, dc):
        super().__init__(dc)

    def get_line_dy(self, height):
        return height * 12

    def get_extents(self, word, style):
        self.dc.set_style(style)
        sizes = self.dc.ctx.text_extents(word + ".")[:4]
        dx = sizes[2]
        dy_up = -1 * sizes[1]
        dy_down = sizes[3] - dy_up
        sizes2 = self.dc.ctx.text_extents(".")[:4]
        dx_space = sizes2[2]
        dx -= dx_space
        if word[-1] != " ":
            dx_space = 0
        return dx, dx_space, dy_up, dy_down

    def get_text_width(self, txt, style):
        self.dc.set_style(style)
        x_off, y_off, tw, th = self.dc.ctx.text_extents(txt)[:4]
        return tw

    def get_text_height(self, txt, style):
        self.dc.set_style(style)
        x_off, y_off, tw, th = self.dc.ctx.text_extents(txt)[:4]
        return th

    def get_img_size(self, png_data):
        try:
            png_stream = io.BytesIO(png_data)
            surface = cairo.ImageSurface.create_from_png(png_stream)
        except Exception:
            surface = None
        if surface:
            return surface.get_width(), surface.get_height()
        return 0, 0


def get_PdfCairoDc(result, width, height):
    surf = cairo.PDFSurface(result, width, height)
    ctx = cairo.Context(surf)
    return CairoDc(ctx=ctx, calc_only=False, width=width, height=height)
