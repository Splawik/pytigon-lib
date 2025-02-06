import os
import io
import fpdf
from pytigon_lib.schhtml.basedc import BaseDc, BaseDcInfo
from pytigon_lib.schfs.vfstools import get_temp_filename
from pytigon_lib.schtools.main_paths import get_main_paths

try:
    import PIL
except ImportError:
    PIL = None

_cfg = get_main_paths()
fpdf.fpdf.FPDF_FONT_DIR = os.path.join(_cfg["STATIC_PATH"], "fonts")


class PDFSurface:
    """Handles PDF surface creation and font management."""

    def __init__(self, output_name, output_stream, width, height):
        """Initialize PDF surface with given dimensions and output settings."""
        self.output_name = output_name
        self.output_stream = output_stream
        self.width = width
        self.height = height
        self.pdf = fpdf.FPDF(unit="pt", orientation="L" if width > height else "P")

        self._add_fonts()
        self.fonts_map = {
            "sans-serif": "sans-serif",
            "serif": "serif",
            "monospace": "monospace",
            "cursive": "sans-serif",
            "fantasy": "sans-serif",
        }

        self.pdf.set_font("sans-serif", "", 11)

    def _add_fonts(self):
        """Add necessary fonts to the PDF."""
        fonts = [
            ("sans-serif", "", "DejaVuSansCondensed.ttf"),
            ("sans-serif", "B", "DejaVuSansCondensed-Bold.ttf"),
            ("sans-serif", "I", "DejaVuSansCondensed-Oblique.ttf"),
            ("sans-serif", "BI", "DejaVuSansCondensed-BoldOblique.ttf"),
            ("serif", "", "DejaVuSerifCondensed.ttf"),
            ("serif", "B", "DejaVuSerifCondensed-Bold.ttf"),
            ("serif", "I", "DejaVuSerifCondensed-Italic.ttf"),
            ("serif", "BI", "DejaVuSerifCondensed-BoldItalic.ttf"),
            ("monospace", "", "DejaVuSansMono.ttf"),
            ("monospace", "B", "DejaVuSansMono-Bold.ttf"),
            ("monospace", "I", "DejaVuSansMono-Oblique.ttf"),
            ("monospace", "BI", "DejaVuSansMono-BoldOblique.ttf"),
        ]
        for family, style, filename in fonts:
            self.pdf.add_font(family, style, filename, uni=True)

    def get_dc(self):
        """Return the PDF drawing context."""
        return self.pdf

    def save(self):
        """Save the PDF to the specified output."""
        if self.output_stream:
            self.pdf.output(self.output_stream)
        else:
            self.pdf.output(self.output_name)


class PdfDc(BaseDc):
    """PDF drawing context that extends BaseDc."""

    def __init__(
        self,
        dc=None,
        calc_only=False,
        width=None,
        height=None,
        output_name=None,
        output_stream=None,
        scale=1.0,
        notify_callback=None,
        record=False,
    ):
        """Initialize the PDF drawing context."""
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
        width2 = self.width if self.width >= 0 else self.default_width
        height2 = self.height if self.height >= 0 else self.default_height

        self.dc_info = PdfDcInfo(self)
        self.type = None

        if self.calc_only:
            self.surf = PDFSurface(None, None, 10, 10)
            self.width = -1 if not width or width < 0 else width
            self.height = 1000000000 if not height or height < 0 else height
            self.dc = self.surf.get_dc()
        else:
            if dc:
                self.surf = None
                self.dc = dc
            else:
                self.surf = PDFSurface(output_name, output_stream, width2, height2)
                self.dc = self.surf.get_dc()

        self._init_drawing_state()

        if self.notify_callback:
            self.notify_callback("start", {"dc": self})

        self.start_page()

    def _init_drawing_state(self):
        """Initialize the drawing state variables."""
        self.last_style_tab = None
        self._color = (0, 0, 0, 255)
        self._line_width = 0
        self._fun_stack = []
        self._fill = False
        self._draw = False
        self._preserve = False
        self._last_pen = None
        self._last_brush = None
        self._last_pen_color = (0, 0, 0, 255)
        self._last_line_width = -1
        self._last_brush_color = (255, 255, 255, 255)

    def close(self):
        """Close the PDF and save it."""
        if self.notify_callback:
            self.notify_callback("end", {"dc": self})

        if not self.calc_only:
            self.surf.save()

    def set_scale(self, scale):
        """Set the scale for the drawing context."""
        self.scale = scale
        self._last_line_width = -1
        self._last_pen = None
        return super().set_scale(scale)

    def _add(self, fun, args):
        """Add a drawing function to the stack."""
        self._fun_stack.append((fun, args))

    def _draw_and_fill(self):
        """Execute all drawing functions in the stack."""
        for fun, args in self._fun_stack:
            fun(*args)

    def start_page(self):
        """Start a new page in the PDF."""
        self.dc.add_page()
        super().start_page()

    def end_page(self):
        """End the current page in the PDF."""
        if self.notify_callback:
            self.notify_callback("end_page", {"dc": self})
        super().end_page()

    def draw(self, preserve=False):
        """Draw the current stack of drawing functions."""
        self._draw = True
        self._fill = False

        if (
            self._last_pen_color != self._color
            or self._last_line_width != self._line_width
        ):
            self.dc.set_draw_color(*self._color[:3])
            self.dc.set_text_color(*self._color[:3])
            self.dc.set_line_width(self._line_width)
            self._last_pen_color = self._color
            self._last_line_width = self._line_width

        self._draw_and_fill()
        self._draw = False
        if not preserve:
            self._fun_stack = []
        return super().draw(preserve)

    def fill(self, preserve=False):
        """Fill the current stack of drawing functions."""
        self._draw = False
        self._fill = True
        if self._last_brush_color != self._color:
            self.dc.set_fill_color(*self._color[:3])
            self._last_brush_color = self._color

        self._draw_and_fill()
        self._fill = False
        if not preserve:
            self._fun_stack = []
        return super().fill(preserve)

    def set_color(self, r, g, b, a=255):
        """Set the current drawing color."""
        self._color = (r, g, b, a)
        super().set_color(r, g, b, a)

    def set_line_width(self, width):
        """Set the current line width."""
        self._line_width = width
        super().set_line_width(width)

    def set_style(self, style):
        """Set the current text style."""
        if style == self.last_style:
            return self.last_style_tab

        style_tab = self.dc_info.styles[style].split(";")
        self.last_style_tab = style_tab

        style2 = ""
        if style_tab[3] == "1":
            style2 += "I"
        if style_tab[4] == "1":
            style2 += "B"

        font_name = self.surf.fonts_map.get(style_tab[1], "sans-serif")
        self.dc.set_font(
            font_name,
            style2,
            int((self.scale * self.base_font_size * int(style_tab[2])) / 100),
        )
        r, g, b = self.rgbfromhex(style_tab[0])
        self.dc.set_text_color(r, g, b)
        super().set_style(style)
        return style_tab

    def add_line(self, x, y, dx, dy):
        """Add a line to the drawing stack."""
        self._add(
            self.dc.line,
            (
                x * self.scale,
                y * self.scale,
                (x + dx) * self.scale,
                (y + dy) * self.scale,
            ),
        )
        super().add_line(x, y, dx, dy)

    def add_rectangle(self, x, y, dx, dy):
        """Add a rectangle to the drawing stack."""
        self._add(
            self._rect,
            (x * self.scale, y * self.scale, dx * self.scale, dy * self.scale),
        )
        super().add_rectangle(x, y, dx, dy)

    def add_rounded_rectangle(self, x, y, dx, dy, radius):
        """Add a rounded rectangle to the drawing stack."""
        self._add(
            self._rect_rounded,
            (x * self.scale, y * self.scale, dx * self.scale, dy * self.scale),
        )
        super().add_rounded_rectangle(x, y, dx, dy, radius)

    def add_arc(self, x, y, radius, angle1, angle2):
        """Add an arc to the drawing stack."""
        super().add_arc(x, y, radius, angle1, angle2)

    def add_ellipse(self, x, y, dx, dy):
        """Add an ellipse to the drawing stack."""
        super().add_ellipse(x, y, dx, dy)

    def add_polygon(self, xytab):
        """Add a polygon to the drawing stack."""
        super().add_polygon(xytab)

    def add_spline(self, xytab, close):
        """Add a spline to the drawing stack."""
        super().add_spline(xytab)

    def draw_text(self, x, y, txt):
        """Draw text at the specified coordinates."""
        dx, dx_space, dy_up, dy_down = self.dc_info.get_extents(txt)
        self.dc.text(x * self.scale, y * self.scale - dy_down - 2, txt)
        super().draw_text(x, y, txt)

    def draw_rotated_text(self, x, y, txt, angle):
        """Draw rotated text at the specified coordinates."""
        w, h, d, e = self.dc_info.get_extents(txt)
        super().draw_rotated_text(x, y, txt)

    def draw_image(self, x, y, dx, dy, scale, png_data):
        """Draw an image at the specified coordinates."""
        if not PIL:
            raise ImportError("PIL is required to draw images.")

        png_stream = io.BytesIO(png_data)
        image = PIL.Image.open(png_stream)
        w, h = image.size
        x_scale, y_scale = self._scale_image(x, y, dx, dy, scale, w, h)

        if scale < 4:
            if scale != 0 and x_scale < 0.25 and y_scale < 0.25:
                image.thumbnail((4 * w * x_scale, 4 * h * y_scale), PIL.Image.LANCZOS)
            file_name = get_temp_filename("temp.png")
            image.save(file_name, "PNG")
            self.dc.image(file_name, x, y, w * x_scale, h * y_scale)
            os.remove(file_name)
        super().draw_image(x, y, dx, dy, scale, png_data)

    def _polygon(self, points):
        """Draw a polygon from a list of points."""
        old_point = None
        for point in points:
            if old_point:
                self.dc.line(
                    int(old_point[0]), int(old_point[1]), int(point[0]), int(point[1])
                )
            old_point = point

    def _rect(self, x, y, dx, dy):
        """Draw a rectangle."""
        if self._fill and not self._draw:
            return self.dc.rect(x, y, dx, dy, "F")
        elif not self._fill and self._draw:
            return self.dc.rect(x, y, dx, dy, "D")
        else:
            return self.dc.rect(x, y, dx, dy, "DF")

    def _rect_rounded(self, x, y, dx, dy):
        """Draw a rounded rectangle."""
        if self._fill and not self._draw:
            return self.dc.rect(x, y, dx, dy, "F")
        elif not self._fill and self._draw:
            delta = 12
            points = [
                (x + delta, y),
                (x + dx - delta, y),
                (x + dx - delta / 2, y + delta / 6),
                (x + dx - delta / 6, y + delta / 2),
                (x + dx, y + delta),
                (x + dx, y + dy - delta),
                (x + dx - delta / 6, y + dy - delta / 2),
                (x + dx - delta / 2, y + dy - delta / 6),
                (x + dx - delta, y + dy),
                (x + delta, y + dy),
                (x + delta / 2, y + dy - delta / 6),
                (x + delta / 6, y + dy - delta / 2),
                (x, y + dy - delta),
                (x, y + delta),
                (x + delta / 6, y + delta / 2),
                (x + delta / 2, y + delta / 6),
                (x + delta, y),
            ]
            self._polygon(points)
        else:
            return self.dc.rect(x, y, dx, dy, "DF")


class PdfDcInfo(BaseDcInfo):
    """PDF drawing context information."""

    def __init__(self, dc):
        """Initialize the PDF drawing context information."""
        super().__init__(dc)

    def get_line_dy(self, height):
        """Get the line height."""
        return height

    def get_extents(self, word, style=None):
        """Get the extents of a word."""
        if style is not None:
            self.dc.set_style(style)

        w = self.dc.dc.get_string_width(word)
        dx = w
        dy_up = self.dc.dc.font_size_pt
        dy_down = 0
        dx_space = self.dc.dc.get_string_width(" ")
        if not word or word[-1] != " ":
            dx_space = 0
        return dx, dx_space, dy_up, dy_down

    def get_text_width(self, txt, style=None):
        """Get the width of a text string."""
        if style is not None:
            self.dc.set_style(style)
        return self.dc.dc.get_string_width(txt)

    def get_text_height(self, txt, style=None):
        """Get the height of a text string."""
        if style:
            self.dc.set_style(style)
        return self.dc.dc.font_size_pt

    def get_img_size(self, png_data):
        """Get the size of an image."""
        try:
            png_stream = io.BytesIO(png_data)
            image = PIL.Image.open(png_stream)
        except Exception:
            image = None
        return image.size if image else (0, 0)
