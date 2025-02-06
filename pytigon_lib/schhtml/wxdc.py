import wx
from pytigon_lib.schhtml.basedc import BaseDc, BaseDcInfo
import io


class DcDc(BaseDc):
    def __init__(
        self,
        dc=None,
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
        self.dc_info = DcDcinfo(self)
        self.width = self.width if self.width >= 0 else self.default_width
        self.height = self.height if self.height >= 0 else self.default_height
        self.type = None

        if self.calc_only:
            self.surf = wx.Bitmap(10, 10, 32)
            self.dc = wx.MemoryDC(self.surf)
            self.dc.Clear()
            if width < 0:
                self.width = -1
            if height < 0:
                self.height = 1000000000
        else:
            if dc:
                self.surf = None
                self.dc = dc
            else:
                if output_name:
                    name = output_name.lower()
                    self.surf = wx.EmptyBitmap(self.width, self.height, 32)
                    self.dc = wx.MemoryDC(self.surf)
                    self.dc.Clear()
                    self.type = "jpg" if ".jpg" in name or ".jpeg" in name else "png"
                else:
                    self.surf = wx.EmptyBitmap(10, 10, 32)
                    self.dc = wx.MemoryDC(self.surf)

        self.last_style_tab = None
        self._color = (0, 0, 0, 255)
        self._line_width = 0
        self._fun_stack = []
        self._fill = False
        self._draw = False
        self._preserve = False
        self.transparent_brush = wx.Brush(
            wx.Colour(255, 255, 255), style=wx.TRANSPARENT
        )
        self.transparent_pen = wx.Pen(
            wx.Colour(255, 255, 255), width=0, style=wx.TRANSPARENT
        )
        self._last_pen = None
        self._last_brush = wx.Brush(wx.Colour(255, 255, 255), style=wx.SOLID)
        self._last_pen_color = (0, 0, 0, 255)
        self._last_line_width = -1
        self._last_brush_color = (255, 255, 255, 255)

    def close(self):
        if not self.calc_only and self.type:
            img = self.surf.ConvertToImage()
            ext = wx.BITMAP_TYPE_JPEG if self.type == "jpg" else wx.BITMAP_TYPE_PNG
            if self.output_stream:
                img.SaveFile(self.output_stream, ext)
            else:
                img.SaveFile(self.output_name, ext)

    def set_scale(self, scale):
        self.scale = scale
        self._last_line_width = -1
        self._last_pen = None
        return super().set_scale(scale)

    def _add(self, fun, args):
        self._fun_stack.append((fun, args))

    def _spline(self, points):
        self.dc.DrawSpline(points)

    def _draw_and_fill(self):
        for fun, args in self._fun_stack:
            fun(*args)

    def start_page(self):
        self.dc.StartPage()
        super().start_page()

    def end_page(self):
        self.dc.EndPage()
        super().end_page()

    def draw(self, preserve=False):
        self._draw = True
        self._fill = False
        self.dc.SetBrush(self.transparent_brush)
        if (
            self._last_pen_color != self._color
            or self._last_line_width != self._line_width
        ):
            self._last_pen = wx.Pen(
                wx.Colour(*self._color[:3]),
                int((self._line_width + 0.49) * self.scale),
                style=wx.SOLID,
            )
            self._last_pen_color = self._color
            self._last_line_width = self._line_width
        self.dc.SetPen(self._last_pen)
        self._draw_and_fill()
        self._draw = False
        if not preserve:
            self._fun_stack = []
        return super().draw(preserve)

    def fill(self, preserve=False):
        self._draw = False
        self._fill = True
        self.dc.SetPen(self.transparent_pen)
        if self._last_brush_color != self._color:
            self._last_brush = wx.Brush(wx.Colour(*self._color[:3]), style=wx.SOLID)
            self._last_brush_color = self._color
        self.dc.SetBrush(self._last_brush)
        self._draw_and_fill()
        self._fill = False
        if not preserve:
            self._fun_stack = []
        return super().fill(preserve)

    def set_color(self, r, g, b, a=255):
        self._color = (r, g, b, a)
        super().set_color(r, g, b, a)

    def set_line_width(self, width):
        self._line_width = width
        super().set_line_width(width)

    def set_style(self, style):
        if style == self.last_style:
            return self.last_style_tab
        style_tab = self.dc_info.styles[style].split(";")
        self.last_style_tab = style_tab
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        font_family_map = {
            "serif": wx.ROMAN,
            "sans-serif": wx.SWISS,
            "monospace": wx.MODERN,
            "cursive": wx.SCRIPT,
            "fantasy": wx.DECORATIVE,
        }
        font.SetFamily(font_family_map.get(style_tab[1], wx.DEFAULT))
        face_name = "DejaVu Serif"
        font.SetFaceName(face_name)
        font.SetWeight(wx.BOLD if style_tab[4] == "1" else wx.FONTWEIGHT_NORMAL)
        font.SetStyle(wx.ITALIC if style_tab[3] == "1" else wx.NORMAL)
        font.SetPointSize(
            int(
                (self.scale * (self.base_font_size * 72) * int(style_tab[2]))
                / (96 * 100.0)
            )
        )
        self.dc.SetFont(font)
        r, g, b = self.rgbfromhex(style_tab[0])
        self.dc.SetTextForeground(wx.Colour(r, g, b))
        self.set_color(r, g, b)
        super().set_style(style)
        return style_tab

    def add_line(self, x, y, dx, dy):
        self._add(
            self.dc.DrawLine,
            (
                int(x * self.scale),
                int(y * self.scale),
                int((x + dx) * self.scale),
                int((y + dy) * self.scale),
            ),
        )
        super().add_line(x, y, dx, dy)

    def add_rectangle(self, x, y, dx, dy):
        self._add(
            self.dc.DrawRectangle,
            (
                int(x * self.scale),
                int(y * self.scale),
                int(dx * self.scale),
                int(dy * self.scale),
            ),
        )
        super().add_rectangle(x, y, dx, dy)

    def add_rounded_rectangle(self, x, y, dx, dy, radius):
        self._add(
            self.dc.DrawRoundedRectangle,
            (
                int(x * self.scale),
                int(y * self.scale),
                int(dx * self.scale),
                int(dy * self.scale),
                radius * self.scale,
            ),
        )
        super().add_rounded_rectangle(x, y, dx, dy, radius)

    def add_arc(self, x, y, radius, angle1, angle2):
        self._add(
            self.dc.DrawEllipticArc,
            (
                int((x + radius) * self.scale),
                int((y + radius) * self.scale),
                int(radius * 2 * self.scale),
                int(radius * 2 * self.scale),
                (360 - angle1) * self.scale,
                (360 - angle2) * self.scale,
            ),
        )
        super().add_arc(x, y, radius, angle1, angle2)

    def add_ellipse(self, x, y, dx, dy):
        self._add(
            self.dc.DrawEllipse,
            (
                int(x * self.scale),
                int(y * self.scale),
                int(dx * self.scale),
                int(dy * self.scale),
            ),
        )
        super().add_ellipse(x, y, dx, dy)

    def add_polygon(self, xytab):
        tabpoints = [
            wx.Point(int(pos[0] * self.scale), int(pos[1] * self.scale))
            for pos in xytab
        ]
        self._add(self.dc.DrawPolygon, (tabpoints,))
        super().add_polygon(xytab)

    def add_spline(self, xytab, close):
        tabpoints = [
            wx.Point(int(pos[0] * self.scale), int(pos[1] * self.scale))
            for pos in xytab
        ]
        self._add(self._spline, (tabpoints,))
        super().add_spline(xytab)

    def draw_text(self, x, y, txt):
        w, h, d, e = self.dc.GetFullTextExtent(txt)
        dy_up = h - d
        self.dc.DrawText(txt, int(x * self.scale), int(y * self.scale - dy_up))
        super().draw_text(x, y, txt)

    def draw_rotated_text(self, x, y, txt, angle):
        w, h, d, e = self.dc.GetFullTextExtent(txt)
        dy_up = h - d
        self.dc.DrawRotatedText(
            txt, int(x * self.scale + dy_up), int(y * self.scale), 360 - int(angle)
        )
        super().draw_rotated_text(x, y, txt)

    def draw_image(self, x, y, dx, dy, scale, png_data):
        png_stream = io.BytesIO(png_data)
        image = wx.ImageFromStream(png_stream)
        w, h = image.GetWidth(), image.GetHeight()
        x_scale, y_scale = self._scale_image(x, y, dx, dy, scale, w, h)
        if scale < 4:
            image.Rescale(int(w * x_scale * self.scale), int(h * y_scale * self.scale))
            bmp = image.ConvertToBitmap()
            self.dc.DrawBitmap(bmp, int(x * self.scale), int(y * self.scale))
        else:
            delta_x, delta_y = 0, 0
            while delta_y < dy:
                if scale == 4 and delta_y > 0:
                    break
                delta_x = 0
                if self.scale != 1:
                    image.Rescale(
                        int(image.width * self.scale), int(image.height * self.scale)
                    )
                bmp = image.ConvertToBitmap()
                while delta_x < dx:
                    if scale == 5 and delta_x > 0:
                        break
                    self.dc.DrawBitmap(bmp, int(x + delta_x), int(y + delta_y))
                    delta_x += w
                delta_y += h
        super().draw_image(x, y, dx, dy, scale, png_data)


class DcDcinfo(BaseDcInfo):
    def __init__(self, dc):
        super().__init__(dc)

    def get_line_dy(self, height):
        return height * 3

    def get_extents(self, word, style):
        self.dc.set_style(style)
        w, h, d, e = self.dc.dc.GetFullTextExtent(f"-{word}-")
        dx = w
        dy_up = h - d
        dy_down = h - dy_up
        w2, h2 = self.dc.dc.GetTextExtent("-")
        dx_space = w2
        dx -= 2 * dx_space
        if word[-1] != " ":
            dx_space = 0
        return dx, dx_space, dy_up, dy_down

    def get_text_width(self, txt, style):
        self.dc.set_style(style)
        tw, th = self.dc.dc.GetTextExtent(txt)
        return tw

    def get_text_height(self, txt, style):
        self.dc.set_style(style)
        tw, th = self.dc.dc.GetTextExtent(txt)
        return th

    def get_img_size(self, png_data):
        try:
            png_stream = io.BytesIO(png_data)
            image = wx.Image(png_stream)
            return image.GetWidth(), image.GetHeight()
        except Exception:
            return 0, 0
