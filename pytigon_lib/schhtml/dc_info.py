"""Device-context info classes for schhtml."""


class BaseDcInfoCommon:
    """Shared text-measurement stubs for device-context info classes."""

    def __init__(self, dc):
        self.dc = dc
        self.styles = []

    def get_text_width(self, txt, style):
        return 12 * len(txt)

    def get_text_height(self, txt, style):
        return 12

    def get_line_dy(self, height):
        return height * 12


class BaseDcInfo(BaseDcInfoCommon):
    def get_multiline_text_width(self, txt, style="default"):
        txt_tab = txt.split(" ")
        minsize = 0
        for word in txt_tab:
            size = self.get_text_width(word, style)
            if size > minsize:
                minsize = size
        maxsize = self.get_text_width(txt, style)
        if len(txt_tab) > 16:
            optsize = (maxsize * 16) / len(txt_tab)
        else:
            optsize = maxsize
        return (optsize, minsize, maxsize)

    def get_multiline_text_height(self, txt, width, style="default"):
        lines = []
        line = ""
        line_ok = ""
        dy = 0
        txt_tab = txt.dc.split(" ")
        for pos in txt_tab:
            if line == "":
                line = pos
            else:
                line = line + " " + pos
            if self.get_text_width(line, style) > width:
                lines.append(line_ok)
                dy += self.get_text_height(line_ok, style)
                line = pos
                line_ok = pos
            else:
                line_ok = line
        if line_ok != "":
            lines.append(line_ok)
            dy += self.get_text_height(line_ok, style)
        return (dy, lines)

    def get_extents(self, word, style):
        dx = self.get_text_width(word, style)
        dx_space = self.get_text_width(" ", style)
        dy = self.get_text_height(word, style)
        dy_up = dy / 2
        dy_down = dy - dy_up
        return (dx, dx_space, dy_up, dy_down)

    def get_style_id(self, style):
        i = 0
        for pos in self.styles:
            if style == pos:
                return i
            i += 1
        self.styles.append(style)
        return i


class NullDcinfo(BaseDcInfoCommon):
    def get_multiline_text_width(self, txt, style="default"):
        return 100

    def get_multiline_text_height(self, txt, width, style="default"):
        return (100, [])

    def get_extents(self, word, style):
        return (100, 0, 0, 20)

    def get_style_id(self, style):
        return 0
