from pytigon_lib.schhtml.htmltools import superstrip

# Define symbols to decode
DECODE_SYM = (
    ("&gt;", ">"),
    ("&lt;", "<"),
    ("&amp;", "&"),
    ("&quot;", '"'),
)


def unescape(text):
    """Unescape HTML entities in the given text."""
    for symbol, replacement in DECODE_SYM:
        text = text.replace(symbol, replacement)
    return text


class Atom:
    """Base rendered element."""

    def __init__(self, data, dx, dx_space, dy_up, dy_down, style=-1, is_txt=False):
        self.data = data
        self.dx = dx
        self.dx_space = dx_space
        self.dy_up = dy_up
        self.dy_down = dy_down
        self.style = style
        self.parent = None
        self.is_txt = is_txt

    def get_width(self):
        """Return the width of the atom."""
        return self.dx

    def get_height(self):
        """Return the height of the atom."""
        return self.dy_up + self.dy_down

    def set_parent(self, parent):
        """Set the parent of the atom."""
        self.parent = parent

    def get_parent(self):
        """Return the parent of the atom."""
        return self.parent


class NullAtom(Atom):
    """Null atom with no content."""

    def __init__(self):
        super().__init__("", 0, 0, 0, 0)

    def draw_atom(self, dc, style, x, y):
        """Draw the atom (no-op)."""
        return True


class BrAtom(NullAtom):
    """Line break atom."""

    def __init__(self, cr_count=1):
        super().__init__()
        self.cr_count = cr_count


class AtomLine:
    """Represents a full line in rendered HTML."""

    def __init__(self, maxwidth):
        self.maxwidth = maxwidth
        self.dx = 0
        self.space = 0
        self.dy_up = 0
        self.dy_down = 0
        self.objs = []
        self.not_justify = False

    def _append(self, atom):
        """Append an atom to the line."""
        self.objs.append(atom)
        self.dx += atom.get_width()
        self.space = atom.dx_space
        self.dy_up = max(self.dy_up, atom.dy_up)
        self.dy_down = max(self.dy_down, atom.dy_down)

    def justify(self, from_second=False):
        """Justify the line by adding space between atoms."""
        if self.not_justify:
            return
        dx = self.maxwidth - self.dx
        d = 1 if from_second else 0
        l = len(self.objs)
        if l > 1 + d:
            for e in self.objs:
                if isinstance(e, BrAtom):
                    return
            ddx = dx / (l - 1 - d)
            objs = []
            for i, obj in enumerate(self.objs):
                objs.append(obj)
                if i == 0 and from_second:
                    continue
                if i < len(self.objs) - 1:
                    n = NullAtom()
                    n.dx = ddx
                    objs.append(n)
            self.objs = objs

    def append(self, atom, force_append=False):
        """Append an atom to the line if it fits."""
        if len(self.objs) > 0:
            if (
                force_append
                or (self.dx + atom.get_width()) - atom.dx_space <= self.maxwidth
            ):
                self._append(atom)
                return True
            return False
        else:
            if force_append or atom.get_width() - atom.dx_space <= self.maxwidth:
                self._append(atom)
                return True
            return False

    def pop_if_one_char(self):
        """Pop the last atom if it contains one or two characters."""
        if len(self.objs) > 2:
            a = self.objs[-1]
            if a.is_txt and len(a.data) <= 2:
                self.dx -= a.dx
                self.objs = self.objs[:-1]
                return a
        return None

    def get_height(self):
        """Return the height of the line."""
        return self.dy_up + self.dy_down


class AtomList:
    """List of atoms to be rendered."""

    def __init__(self, dc_info, line_dy=0, pre=False):
        self.dc_info = dc_info
        self.atom_list = []
        self.line_dy = dc_info.get_line_dy(line_dy)
        self.list_for_draw = None
        self.first_line_height = -1
        self.first_line_offset = 0
        self.width = -1
        self.pre = pre
        self.justify = False
        self.leave_single_char = True

    def set_first_line_offset(self, offset):
        """Set the offset for the first line."""
        self.first_line_offset = offset

    def set_justify(self, justify=True):
        """Set whether to justify the text."""
        self.justify = justify

    def set_leave_single_char(self, leave=True):
        """Set whether to leave single characters on a line."""
        self.leave_single_char = leave

    def set_line_dy(self, dy):
        """Set the line spacing."""
        self.line_dy = self.dc_info.get_line_dy(dy)

    def append_text(self, text, style, parent=None):
        """Append text to the atom list."""
        if not text:
            return

        if not self.pre:
            text = unescape(text.replace("\n", " "))
        else:
            if "\n" in text:
                lines = unescape(text).split("\n")
                self.append_text(lines[0], style, parent)
                last_br = None
                for line in lines[1:]:
                    if line:
                        if last_br:
                            last_br.cr_count += 1
                        else:
                            last_br = BrAtom()
                            self.append_atom(BrAtom())
                        self.append_text(line, style, parent)
                        last_br = None
                    else:
                        if last_br:
                            last_br.cr_count += 1
                        else:
                            last_br = BrAtom()
                            self.append_atom(last_br)
                return
            else:
                text = unescape(text)

        words = superstrip(text).split(" ")
        if text[0] == " ":
            words[0] = " " + words[0]
        for i in range(len(words) - 1):
            words[i] += " "
        if text[-1] == " ":
            words[-1] += " "
            if words[-1] == "  ":
                words[-1] = " "

        if self.pre or (parent and parent.no_wrap):
            if text:
                extents = self.dc_info.get_extents(text, style)
                atom = Atom(
                    text, extents[0], extents[1], extents[2], extents[3], style, True
                )
                atom.set_parent(parent)
                self.atom_list.append(atom)
        else:
            for word in words:
                if not word:
                    continue
                extents = self.dc_info.get_extents(word, style)
                atom = Atom(
                    word, extents[0], extents[1], extents[2], extents[3], style, True
                )
                if parent:
                    atom.set_parent(parent)
                self.atom_list.append(atom)

    def append_atom(self, atom):
        """Append an atom to the list."""
        self.atom_list.append(atom)

    def get_width_tab(self):
        """Calculate the optimal, minimum, and maximum width of the atom list."""
        minwidth = 0
        maxwidth = 0
        maxmaxwidth = 0
        for atom in self.atom_list:
            minwidth = max(minwidth, atom.get_width())
            maxwidth += atom.get_width() + atom.dx_space
            if isinstance(atom, BrAtom):
                maxmaxwidth = max(maxmaxwidth, maxwidth)
                maxwidth = 0

        maxwidth = max(maxwidth, maxmaxwidth)
        optwidth = (
            (maxwidth * 8) // len(self.atom_list)
            if len(self.atom_list) > 8
            else maxwidth
        )
        return (optwidth, minwidth, maxwidth)

    def gen_list_for_draw(self, width):
        """Generate a list of lines for drawing."""
        lines = []
        last_atom = None
        line = AtomLine(width)
        for atom in self.atom_list:
            if isinstance(atom, BrAtom):
                if atom.cr_count > 1:
                    line.dy_down += line.get_height() * (atom.cr_count - 1)
                line.not_justify = True
                lines.append(line)
                line = AtomLine(width)
                continue

            test_append = True
            if atom.is_txt and atom.data == " ":
                if (
                    not last_atom
                    or (last_atom.is_txt and last_atom.data[-1] == " ")
                    or "CtrlTag" in last_atom.data.__class__.__name__
                ):
                    test_append = False

            if test_append:
                if not line.append(atom):
                    if not self.leave_single_char:
                        c = line.pop_if_one_char()
                    else:
                        c = None
                    lines.append(line)
                    line = AtomLine(width)
                    if c:
                        line.append(c, force_append=True)
                    line.append(atom, force_append=True)
            last_atom = atom

        if line.objs:
            lines.append(line)
            if self.first_line_height == -1:
                self.first_line_height = line.get_height()

        for i, line in enumerate(lines):
            if i == 0:
                line.maxwidth -= self.first_line_offset
            if self.justify and i < len(lines) - 1:
                line.justify(from_second=(i == 0 and self.first_line_offset != 0))

        self.list_for_draw = lines
        self.width = width

    def get_height(self):
        """Return the total height of the atom list."""
        if not self.list_for_draw:
            return -1
        dy = sum(line.get_height() for line in self.list_for_draw)
        dy += self.line_dy * (len(self.list_for_draw) - 1)
        return dy

    def draw_atom_list(self, dc, align=0, valign=1):
        """Draw the atom list on the given device context."""
        size = dc.get_size()
        if size[0] == -1:
            size[0] = self.width

        y = 0
        if valign > 0:
            y2 = self.get_height()
            if valign == 1:
                y = (size[1] - y2) // 2
            else:
                y = size[1] - y2

        if self.list_for_draw:
            first = True
            for line in self.list_for_draw:
                if line.objs:
                    if align == 0:
                        x = 0
                    else:
                        x = (
                            (size[0] - line.dx + line.space) // 2
                            if align == 1
                            else size[0] - line.dx + line.space
                        )
                    subdc = dc.subdc(x, y, size[0] - x, line.get_height())
                    subdc.draw_atom_line(
                        self.first_line_offset if first else 0, 0, line
                    )
                    y += line.get_height() + self.line_dy
                    first = False

        self.list_for_draw = []
        self.atom_list = []
        return y - self.line_dy

    def to_txt(self):
        """Convert the atom list to a plain text string."""
        return "".join(
            atom.data for atom in self.atom_list if isinstance(atom.data, str)
        )

    def to_attrs(self):
        """Convert the atom list to a dictionary of attributes."""
        attrs = {}
        for atom in self.atom_list:
            if atom.parent:
                for attr in atom.parent.attrs:
                    if attr not in attrs:
                        attrs[attr] = atom.parent.attrs[attr]
                attrs["data"] = atom.data
        return attrs

    def to_obj_tab(self):
        """Convert the atom list to a dictionary of objects."""
        objs = {}
        for atom in self.atom_list:
            if atom.parent and atom.parent.sys_id not in objs:
                objs[atom.parent.sys_id] = atom.parent
        return objs
