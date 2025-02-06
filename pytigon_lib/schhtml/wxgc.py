import wx
import io
from pytigon_lib.schhtml.basedc import BaseDc, BaseDcInfo


class GraphicsContextDc(BaseDc):
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
        self.dc_info = GraphicsContextDcinfo(self)
        self.type = None
        self.path = None
        self.colour = wx.Colour(0, 0, 0)
        self.line_width = 1
        self._move_x = 0
        self._move_y = 0
        self.last_style_tab = None

        if self.calc_only:
            self.surf = wx.EmptyBitmap(10, 10, 32)
            dc = wx.MemoryDC(self.surf)
            dc.Clear()
            self.ctx = self._make_gc(dc)
            self.width = -1 if width < 0 else width
            self.height = 1000000000 if height < 0 else height
        else:
            if ctx:
                self.surf = None
                self.ctx = ctx
            else:
                width2 = self.width if self.width >= 0 else self.default_width
                height2 = self.height if self.height >= 0 else self.default_height
                self.surf = wx.EmptyBitmap(width2, height2, 32)
                if output_name:
                    self.type = "png"
                dc = wx.MemoryDC(self.surf)
                dc.Clear()
                self.ctx = self._make_gc(dc)

    def _make_gc(self, dc):
        try:
            return wx.GraphicsContext.Create(dc)
        except NotImplementedError:
            dc.DrawText(
                "This build of wxPython does not support the wx.GraphicsContext family of classes.",
                25,
                25,
            )
            return None

    def close(self):
        if not self.calc_only and self.type == "png":
            image = self.surf.ConvertToImage()
            if self.output_stream:
                image.SaveFile(self.output_stream, wx.BITMAP_TYPE_PNG)
            else:
                image.SaveFile(self.output_name, wx.BITMAP_TYPE_PNG)

    def new_page(self):
        super().new_page()

    def new_path(self):
        self.path = self.ctx.CreatePath()
        super().new_path()

    def stroke(self):
        if not self.calc_only:
            self.ctx.StrokePath(self.path)
        self.path = None
        super().stroke()

    def fill(self):
        if not self.calc_only:
            self.ctx.FillPath(self.path)
        self.path = None
        super().fill()

    def draw(self):
        if not self.calc_only:
            self.ctx.DrawPath(self.path)
        self.path = None
        super().draw()

    def move_to(self, x, y):
        self._move_x = x
        self._move_y = y
        if self.path:
            self.path.MoveToPoint(x, y)
        super().move_to(x, y)

    def line_to(self, x, y):
        self.path.AddLineToPoint(x, y)
        super().move_to(x, y)

    def show_text(self, txt):
        w, h, d, e = self.ctx.GetFullTextExtent(txt)
        dy_up = h - d
        self.ctx.DrawText(txt, self._move_x, self._move_y - dy_up)
        super().show_text(txt)

    def set_pen(self, r, g, b, a=255, width=1):
        pen = wx.Pen(wx.Colour(r, g, b, a))
        self.ctx.SetPen(pen)
        super().set_pen(r, g, b, a, width)

    def set_brush(self, r, g, b, a=255):
        brush = wx.Brush(wx.Colour(r, g, b, a))
        self.ctx.SetBrush(brush)
        super().set_brush(r, g, b, a)

    def set_style(self, style):
        if style == self.last_style:
            return self.last_style_tab
        style_tab = self.dc_info.styles[style].split(";")
        self.last_style_tab = style_tab
        font = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        slant = wx.ITALIC if style_tab[3] == "1" else wx.NORMAL
        weight = wx.BOLD if style_tab[4] == "1" else wx.FONTWEIGHT_NORMAL
        font_families = {
            "serif": wx.ROMAN,
            "sans-serif": wx.SWISS,
            "monospace": wx.MODERN,
            "cursive": wx.SCRIPT,
            "fantasy": wx.DECORATIVE,
        }
        font_style = font_families.get(style_tab[1], wx.DEFAULT)
        font.SetStyle(slant)
        font.SetWeight(weight)
        font.SetFamily(font_style)
        font.SetPointSize((self.base_font_size * int(style_tab[2])) / 100.0)
        self.ctx.SetFont(font)
        r, g, b = self.rgbfromhex(style_tab[0])
        self.ctx.SetPen(wx.Pen(wx.Colour(r, g, b)))
        super().set_style(style)
        return style_tab

    def draw_atom_line(self, x, y, line):
        dx = 0
        for obj in line.objs:
            if obj.style >= 0:
                style = self.set_style(obj.style)
                if style[5] == "1":
                    self.new_path()
                    self.move_to(x + dx, y + line.dy_up + line.dy_down)
                    self.line_to(x + dx + obj.dx, y + line.dy_up + line.dy_down)
                    self.stroke()
            if isinstance(obj.data, str):
                ret = False
                if obj.parent and hasattr(obj.parent, "draw_atom"):
                    ret = obj.parent.draw_atom(
                        self, obj.style, x + dx, (y + line.dy_up) - obj.dy_up
                    )
                if not ret:
                    self.move_to(x + dx, y + line.dy_up)
                    self.show_text(obj.data)
            else:
                obj.data.draw_atom(
                    self, obj.style, x + dx, (y + line.dy_up) - obj.dy_up
                )
            dx += obj.dx

    def rectangle(self, x, y, dx, dy):
        self.path.AddRectangle(x, y, dx, dy)
        super().rectangle(x, y, dx, dy)

    def draw_line(self, x, y, dx, dy):
        self.path.MoveToPoint(x, y)
        self.path.AddLineToPoint(x + dx, y + dy)
        super().draw_line(x, y, dx, dy)

    def draw_image(self, x, y, dx, dy, scale, png_data):
        try:
            png_stream = io.BytesIO(png_data)
            image = wx.ImageFromStream(png_stream)
            w, h = image.GetWidth(), image.GetHeight()
            x_scale, y_scale = self._scale_image(x, y, dx, dy, scale, w, h)
            if scale < 4:
                image.Rescale(w * x_scale, h * y_scale)
                bmp = image.ConvertToBitmap()
                self.ctx.DrawBitmap(bmp, x, y, w, h)
            else:
                delta_x, delta_y = 0, 0
                while delta_y < dy:
                    if scale == 4 and delta_y > 0:
                        break
                    delta_x = 0
                    bmp = image.ConvertToBitmap()
                    while delta_x < dx:
                        if scale == 5 and delta_x > 0:
                            break
                        self.ctx.DrawBitmap(bmp, x + delta_x, y + delta_y, w, h)
                        delta_x += w
                    delta_y += h
        except Exception as e:
            print(f"Error drawing image: {e}")
        super().draw_image(x, y, dx, dy, scale, png_data)


class GraphicsContextDcinfo(BaseDcInfo):
    def __init__(self, dc):
        super().__init__(dc)

    def get_line_dy(self, height):
        return height * 3

    def get_extents(self, word, style):
        self.dc.set_style(style)
        w, h, d, e = self.dc.ctx.GetFullTextExtent("-" + word + "-")
        dx = w
        dy_up = h - d
        dy_down = h - dy_up
        w2, h2 = self.dc.ctx.GetTextExtent("-")
        dx_space = w2
        dx -= 2 * dx_space
        if word[-1] != " ":
            dx_space = 0
        return dx, dx_space, dy_up, dy_down

    def get_text_width(self, txt, style):
        self.dc.set_style(style)
        tw, th = self.dc.ctx.GetTextExtent(txt)
        return tw

    def get_text_height(self, txt, style):
        self.dc.set_style(style)
        tw, th = self.dc.ctx.GetTextExtent(txt)
        return th

    def get_img_size(self, png_data):
        try:
            png_stream = io.BytesIO(png_data)
            image = wx.ImageFromStream(png_stream)
            return image.GetWidth(), image.GetHeight()
        except Exception:
            return 0, 0
