from pytigon_lib.schtools.images import svg_to_png, spec_resize
from django.core.files.storage import default_storage
import PIL
import io


class RenderBase:
    """Base class for rendering attributes."""

    def __init__(self, parent):
        self.parent = parent
        self.rendered_attribs = None

    def get_size(self):
        """Get the size based on rendered attributes."""
        if self.rendered_attribs:
            for attr in self.rendered_attribs:
                if attr in self.parent.attrs:
                    if hasattr(self, "handle_get_size"):
                        return self.handle_get_size(self.parent.attrs[attr])
                    return [0, 0, 0, 0]
        return [0, 0, 0, 0]

    def render(self, dc):
        """Render the attributes on the drawing context."""
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
    """Render background attributes."""

    def __init__(self, parent):
        super().__init__(parent)
        self.rendered_attribs = (
            "bgcolor",
            "background-color",
            "background-image",
            "background",
        )

    def background(self, dc, bgcolor, image_url, repeat, attachment, x, y):
        """Render background color and/or image."""
        if bgcolor:
            r, g, b = dc.rgbfromhex(bgcolor)
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
                img = response.ptr() if response.ret_code != 404 else None
                if isinstance(img, str):
                    img = img.encode("utf-8")
            except Exception:
                img = None

            if img:
                img_name = image_url.lower()
                if ".png" in img_name:
                    img_bytes = img
                elif ".svg" in img_name:
                    itype = self.parent.attrs.get("image-type", "simple")
                    img_bytes = svg_to_png(img, int(dc.dx), int(dc.dy), itype)
                else:
                    with io.BytesIO(img) as img_buffer:
                        image = PIL.Image.open(img_buffer)
                        output = io.BytesIO()
                        image.save(output, "PNG")
                        img_bytes = output.getvalue()

                dc.draw_image(0, 0, dc.dx, dc.dy, style, img_bytes)

    def handle_render(self, dc, attr_name, value):
        """Handle rendering based on attribute name."""
        if attr_name == "background-image":
            img_url = value.replace("url(", "").replace(")", "")
            self.background(dc, None, img_url, None, None, None, None)
        elif attr_name == "background":
            tab_attr = value.split()
            background_color = "#ffffff"
            background_image = ""
            background_repeat = ""
            background_attachment = ""
            background_position_x = ""
            background_position_y = ""

            for pos in tab_attr:
                if "#" in pos:
                    background_color = pos
                elif "url" in pos:
                    background_image = pos.replace("url(", "").replace(")", "")
                elif "repeat" in pos:
                    background_repeat = pos
                elif pos in ("scroll", "fixed", "inherit"):
                    background_attachment = pos
                elif pos in ("left", "center", "right"):
                    background_position_x = pos
                elif pos in ("top", "center", "bottom"):
                    background_position_y = pos

            self.background(
                dc,
                background_color,
                background_image,
                background_repeat,
                background_attachment,
                background_position_x,
                background_position_y,
            )
        elif "#" in value:
            self.background(dc, value, None, None, None, None, None)
        return dc


class RenderBorder(RenderBase):
    """Render border attributes."""

    def __init__(self, parent):
        super().__init__(parent)
        self.rendered_attribs = (
            "border-top",
            "border-right",
            "border-bottom",
            "border-left",
            "border",
        )

    def handle_get_size(self, border):
        """Get border size."""
        return sizes_from_attr(border, self)

    def handle_render(self, dc, attr_name, border):
        """Render border."""
        p = self.handle_get_size(border)
        b = p[0]
        if b > 0:
            if "border-color" in self.parent.attrs:
                r, g, b_color = dc.rgbfromhex(self.parent.attrs["border-color"])
                dc.set_color(r, g, b_color, 255)
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
    """Base class for padding and margin rendering."""

    def __init__(self, parent):
        super().__init__(parent)

    def handle_get_size(self, padding):
        """Get padding/margin size."""
        return sizes_from_attr(padding, self)

    def handle_render(self, dc, attr_name, padding):
        """Render padding/margin."""
        p = self.handle_get_size(padding)
        return dc.subdc(p[0], p[2], (dc.dx - p[0]) - p[1], (dc.dy - p[2]) - p[3])


class RenderCellPadding(RenderPaddingMargin):
    """Render cell padding."""

    def __init__(self, parent):
        super().__init__(parent)
        self.rendered_attribs = ("cellpadding",)


class RenderCellSpacing(RenderPaddingMargin):
    """Render cell spacing."""

    def __init__(self, parent):
        super().__init__(parent)
        self.rendered_attribs = ("cellspacing",)


class RenderPadding(RenderPaddingMargin):
    """Render padding."""

    def __init__(self, parent):
        super().__init__(parent)
        self.rendered_attribs = ("padding",)


class RenderMargin(RenderPaddingMargin):
    """Render margin."""

    def __init__(self, parent):
        super().__init__(parent)
        self.rendered_attribs = ("margin",)


def sizes_from_attr(attr_value, parent):
    """Convert attribute value to size list."""
    if isinstance(attr_value, str):
        sizes = attr_value.strip().replace("px", "").replace("em", "").split()
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
                        while p and p.width <= 0:
                            p = p.parent
                        norm_sizes.append(int(p.width * x / 100) if p else 10)
                    else:
                        p = parent
                        while p and p.height <= 0:
                            p = p.parent
                        norm_sizes.append(int(p.width * x / 100) if p else 10)
                except ValueError:
                    norm_sizes.append(10)
            else:
                try:
                    norm_sizes.append(int(size))
                except ValueError:
                    norm_sizes.append(10)

        if len(sizes) == 1:
            return [norm_sizes[0]] * 4
        elif len(sizes) == 2:
            return [norm_sizes[1], norm_sizes[1], norm_sizes[0], norm_sizes[0]]
        elif len(sizes) == 4:
            return [norm_sizes[3], norm_sizes[1], norm_sizes[0], norm_sizes[2]]
        else:
            print(f"size_from_attr error: {{{attr_value}}}", len(sizes), sizes)
            return [10, 10, 10, 10]
    return attr_value


def get_size(render_list):
    """Get total size from a list of render objects."""
    s = [0, 0, 0, 0]
    for pos in render_list:
        size = pos.get_size()
        s[0] += size[0]
        s[1] += size[1]
        s[2] += size[2]
        s[3] += size[3]
    return s
