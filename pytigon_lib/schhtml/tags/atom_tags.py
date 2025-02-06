import io
import PIL
from pytigon_lib.schhtml.basehtmltags import (
    BaseHtmlAtomParser,
    register_tag_map,
    ATOM_TAGS,
    PAR_TAGS,
)
from pytigon_lib.schhtml.atom import Atom, NullAtom, BrAtom
from pytigon_lib.schhtml.render_helpers import (
    RenderBackground,
    RenderBorder,
    RenderCellSpacing,
    RenderCellPadding,
    RenderPadding,
    RenderMargin,
    get_size,
)
from pytigon_lib.schtools.images import svg_to_png, spec_resize


class AtomTag(BaseHtmlAtomParser):
    """Base class for HTML atom tags."""

    def __init__(self, parent, parser, tag, attrs):
        super().__init__(parent, parser, tag, attrs)
        self.child_tags = (
            ATOM_TAGS + PAR_TAGS + ["table", "form", "comment", "vimg", "ctr*"]
        )
        self.gparent = parent.gparent

    def draw_atom(self, dc, style, x, y, dx, dy):
        """Draw the atom on the device context."""
        parent = self.parent
        while parent:
            if isinstance(parent, Atag):
                return parent.draw_atom(dc, style, x, y, dx, dy)
            parent = parent.parent
        return False

    def close(self):
        """Close the tag and append the atom list to the parent."""
        if self.atom_list:
            self.parent.append_atom_list(self.atom_list)


class BrTag(AtomTag):
    """Class for handling <br> tags."""

    def __init__(self, parent, parser, tag, attrs):
        super().__init__(parent, parser, tag, attrs)

    def close(self):
        """Close the tag and append a BrAtom to the parent."""
        self.make_atom_list()
        self.atom_list.append_atom(BrAtom())
        self.parent.append_atom_list(self.atom_list)


class Atag(AtomTag):
    """Class for handling <a> tags."""

    def __init__(self, parent, parser, tag, attrs):
        super().__init__(parent, parser, tag, attrs)
        self.no_wrap = True

    def set_dc_info(self, dc_info):
        """Set device context information."""
        ret = super().set_dc_info(dc_info)
        self.make_atom_list()
        return ret

    def append_atom_list(self, atom_list):
        """Append an atom list and set parent for each atom."""
        if atom_list:
            for atom in atom_list.atom_list:
                atom.set_parent(self)
                if not atom.is_txt and atom.atom_list:
                    for atom2 in atom.atom_list.atom_list:
                        atom2.set_parent(self)
        super().append_atom_list(atom_list)

    def draw_atom(self, dc, style, x, y, dx, dy):
        """Draw the atom and register the href action."""
        self.reg_action("href", dc.subdc(x, y, dx, dy))
        return False

    def close(self):
        """Close the tag and append the atom list to the parent."""
        atom = NullAtom()
        self.atom_list.append_atom(atom)
        if (
            len(self.atom_list.atom_list) > 1
            and not self.atom_list.atom_list[0].data.strip()
        ):
            self.atom_list.atom_list = self.atom_list.atom_list[1:]

        for atom in self.atom_list.atom_list:
            if not atom.parent:
                atom.set_parent(self)

        self.parent.append_atom_list(self.atom_list)

    def __repr__(self):
        return f"ATag({self.tag};{str(self.attrs)})"


class ImgDraw:
    """Class for drawing images."""

    def __init__(self, img_tag, image, width, height):
        self.img_tag = img_tag
        self.image = image
        self.width = width
        self.height = height

    def draw_atom(self, dc, style, x, y, dx, dy):
        """Draw the image on the device context."""
        if self.image:
            dc.draw_image(x, y, self.width, self.height, 3, self.image)
        else:
            print("null_img")


class ImgTag(AtomTag):
    """Class for handling <img> tags."""

    def __init__(self, parent, parser, tag, attrs):
        super().__init__(parent, parser, tag, attrs)
        self.src = attrs.get("src")
        self.img = None
        self.dx = 0
        self.dy = 0

    def close(self):
        """Close the tag and handle image loading and resizing."""
        if self.width > 0:
            self.dx = self.get_width()[0]
        if self.height > 0:
            self.dy = self.get_height()

        if self.src:
            http = self.parser.get_http_object()
            try:
                response = http.get(self, self.src)
                img = response.ptr() if response.ret_code != 404 else None
                if isinstance(img, str):
                    img = img.encode("utf-8")
            except Exception as e:
                img = None
                print(f"Image {self.src} not loaded! Error: {e}")

            if img:
                img_name = self.src.lower()
                if ".png" in img_name:
                    self.img = img
                elif ".svg" in img_name:
                    itype = self.attrs.get("image-type", "simple")
                    if self.width > 0 and self.height > 0:
                        self.img = svg_to_png(img, self.width, self.height, itype)
                else:
                    try:
                        image = PIL.Image.open(io.BytesIO(img))
                        output = io.BytesIO()
                        image.save(output, "PNG")
                        self.img = output.getvalue()
                    except Exception as e:
                        print(f"Failed to process image {self.src}: {e}")

        if self.img:
            if self.width > 0 and self.height > 0:
                self.dx, self.dy = self.get_width()[0], self.get_height()
            else:
                dx, dy = self.dc_info.get_img_size(self.img)
                if self.width > 0:
                    self.dx = min(self.get_width()[0], self.max_width)
                    self.dy = dy * self.dx / dx
                elif self.height > 0:
                    self.dx = dx * min(self.get_height(), self.max_height) / dy
                    self.dy = self.height
                else:
                    self.dx, self.dy = dx, dy

            self.dx, self.dy = self.take_into_account_minmax(
                self.dx, self.dy, scale=True
            )

            img_atom = Atom(
                ImgDraw(self, self.img, self.dx, self.dy), self.dx, 0, self.dy, 0
            )
            img_atom.set_parent(self)
            self.make_atom_list()
            self.atom_list.append_atom(img_atom)
            self.parent.append_atom_list(self.atom_list)


class ParCalc(AtomTag):
    """Class for handling <calc> tags."""

    def handle_data(self, data):
        """Handle data by evaluating it as a Python expression."""
        parent = self.parent
        while parent:
            if parent.tag == "table":
                table = parent
            if parent.tag == "body":
                body = parent
            if parent.tag == "html":
                html = parent
            parent = parent.parent
        data2 = str(eval(data))
        return super().handle_data(data2)


class HrTag(AtomTag):
    """Class for handling <hr> tags."""

    def __init__(self, parent, parser, tag, attrs):
        super().__init__(parent, parser, tag, attrs)
        self.render_helpers = [RenderMargin(self)]
        self.extra_space = get_size(self.render_helpers)
        self.in_draw = False

    def close(self):
        """Close the tag and append an atom representing the horizontal rule."""
        border = int(self.attrs.get("border", 1))
        atom = Atom(
            self,
            dx=self.width - self.extra_space[0] - self.extra_space[1],
            dx_space=0,
            dy_up=self.extra_space[2] + border,
            dy_down=self.extra_space[3],
        )
        atom.set_parent(self)
        self.make_atom_list()
        self.atom_list.append_atom(atom)
        self.parent.append_atom_list(self.atom_list)

    def draw_atom(self, dc, style, x, y, dx, dy):
        """Draw the horizontal rule on the device context."""
        if self.in_draw:
            return False
        self.in_draw = True
        self.reg_id(dc)
        self.reg_end()
        dc2 = dc.subdc(x, y, dx, dy, True)
        for r in self.render_helpers:
            dc2 = r.render(dc2)
        if "border" in self.attrs:
            dc2.set_line_width(int(self.attrs["border"]))
        dc2.add_line(
            self.extra_space[0],
            self.extra_space[2],
            dx - self.extra_space[0] - self.extra_space[1],
            0,
        )
        dc2.draw()
        self.in_draw = False
        return True


# Register the tags
register_tag_map("br", BrTag)
register_tag_map("a", Atag)
register_tag_map("img", ImgTag)
register_tag_map("calc", ParCalc)
register_tag_map("hr", HrTag)
