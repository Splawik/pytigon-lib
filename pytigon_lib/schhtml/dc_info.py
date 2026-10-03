"""Device-context info classes for schhtml."""


class BaseDcInfoCommon:
    """Shared text-measurement stubs for device-context info classes."""

    def __init__(self, dc):
        self.dc = dc
        self._styles = []
        self._style_ids = {}

    @property
    def styles(self):
        """Distinct style strings seen so far; part of the serialised state."""
        return self._styles

    @styles.setter
    def styles(self, value):
        # basedc.py rebinds this wholesale when restoring saved state, so the
        # lookup index built by get_style_id() must be rebuilt from the new
        # list (first occurrence wins, matching the original linear scan).
        self._styles = value
        self._style_ids = {}
        for i, existing in enumerate(value):
            self._style_ids.setdefault(existing, i)

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
        txt_tab = txt.split(" ")
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
        # Called once per rendered element with a freshly built style string,
        # so a linear scan over the distinct styles made the render O(n*k).
        index = self._style_ids
        i = index.get(style)
        if i is None:
            i = len(self.styles)
            self.styles.append(style)
            index[style] = i
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
