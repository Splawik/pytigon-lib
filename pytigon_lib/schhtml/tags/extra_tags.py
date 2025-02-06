from pytigon_lib.schhtml.basehtmltags import BaseHtmlAtomParser, register_tag_map
from pytigon_lib.schhtml.atom import Atom
from pytigon_lib.schhtml.render_helpers import (
    RenderBackground,
    RenderBorder,
    RenderCellSpacing,
    RenderCellPadding,
    get_size,
)


class VectorImg(BaseHtmlAtomParser):
    """A class to handle vector image tags in HTML."""

    def __init__(self, parent, parser, tag, attrs):
        """Initialize the VectorImg object.

        Args:
            parent: The parent HTML element.
            parser: The HTML parser.
            tag: The HTML tag.
            attrs: The attributes of the HTML tag.
        """
        super().__init__(parent, parser, tag, attrs)
        self.gparent = parent.gparent
        self.render_helpers = [
            RenderCellSpacing(self),
            RenderBorder(self),
            RenderBackground(self),
            RenderCellPadding(self),
        ]
        self.extra_space = get_size(self.render_helpers)
        self.draw_txt = ""
        self.dx = 0
        self.dy = 0

    def _get_pseudo_margins(self):
        """Get the pseudo margins for the element.

        Returns:
            list: A list of margin values [top, right, bottom, left].
        """
        return list(self.extra_space)

    def close(self):
        """Close the VectorImg element and finalize its properties."""
        try:
            if self.width > 0 and self.height > 0:
                self.dx = self.width
                self.dy = self.height
            else:
                self.dx = 100
                self.dy = 100

            img_atom = Atom(self, self.dx, 0, self.dy, 0)
            img_atom.set_parent(self)
            self.make_atom_list()
            self.atom_list.append_atom(img_atom)
            self.parent.append_atom_list(self.atom_list)
        except Exception as e:
            raise RuntimeError(f"Error closing VectorImg: {e}")

    def handle_data(self, data):
        """Handle the data within the VectorImg element.

        Args:
            data: The data to be handled.
        """
        self.draw_txt += data

    def draw_atom(self, dc, style, x, y, dx, dy):
        """Draw the atom on the device context.

        Args:
            dc: The device context.
            style: The style to apply.
            x: The x-coordinate.
            y: The y-coordinate.
            dx: The width.
            dy: The height.

        Returns:
            bool: True if drawing was successful.
        """
        try:
            self.reg_id(dc)
            self.reg_end()
            dc2 = dc.subdc(x, y, self.width, self.height, True)
            for r in self.render_helpers:
                dc2 = r.render(dc2)
            dc2.play_str(self.draw_txt)
            return True
        except Exception as e:
            raise RuntimeError(f"Error drawing atom: {e}")


register_tag_map("vimg", VectorImg)
