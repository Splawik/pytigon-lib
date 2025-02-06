from pytigon_lib.schhtml.basehtmltags import (
    BaseHtmlElemParser,
    register_tag_map,
)
from pytigon_lib.schhtml.render_helpers import (
    RenderBackground,
    RenderBorder,
    RenderPadding,
    RenderMargin,
    get_size,
)
from .p_tags import InlineElements
from pytigon_lib.schhtml.htmltools import HtmlProxyParser


class BodyTag(InlineElements):
    """Handles the <body> tag in HTML, managing rendering and layout."""

    def __init__(self, parent, parser, tag, attrs):
        super().__init__(parent, parser, tag, attrs)
        self.child_tags += ["newpage", "page", "label"]
        self.page = 1
        self.y = 0
        self.border = 0
        self.cellspacing = 0
        self.dc_page = None
        width, height = parent.dc.get_size()
        self.render_helpers = [
            RenderMargin(self),
            RenderBorder(self),
            RenderBackground(self),
            RenderPadding(self),
        ]
        self.extra_space = get_size(self.render_helpers)
        self.margins = list(self.extra_space)
        self.dc = parent.dc.subdc(0, 0, width, height, False)
        self.width, self.height = self.dc.get_size()
        self.width = width if self.width >= 0 else -1
        self.height = height
        self.new_page = 0
        self.reg_id(self.dc)
        self.reg_end()
        self._maxwidth = 0
        self._maxheight = 0
        self.header = None
        self.footer = None
        self.header_height = 0
        self.footer_height = 0
        self.in_footer = False
        self.base_state = None

    def set_dc_info(self, dc_info):
        super().set_dc_info(dc_info)
        self.get_style_id()

    def data_from_child(self, child, data):
        """Process data from child elements like header and footer."""
        if child.tag == "header":
            self.header = data.getvalue()
            self.header_height = int(child.attrs.get("height", 0))
        else:
            self.footer = data.getvalue()
            self.footer_height = int(child.attrs.get("height", 0))
            if self.footer_height == 0:
                self.footer_height = self.height / 10

    def page_changed(self):
        """Handle page change events."""
        if not self.base_state:
            self.base_state = self.dc.state()
        if self.new_page == 0:
            self.render_new_page()

    def print_header(self):
        """Render the header on the current page."""
        if self.header:
            self.dc.paging = False
            self.y = 0
            proxy = HtmlProxyParser(self)
            proxy.feed(self.header)
            self.render_atom_list()
            proxy.close()
            if self.header_height != 0:
                self.y = self.header_height
            self.dc.paging = True

    def print_footer(self):
        """Render the footer on the current page."""
        if self.footer:
            self.dc.paging = False
            self.y = (
                self.height
                - self.extra_space[2]
                - self.extra_space[3]
                - self.footer_height
            )
            self.in_footer = True
            proxy = HtmlProxyParser(self)
            proxy.feed(self.footer)
            proxy.close()
            self.render_atom_list()
            self.in_footer = False
            self.dc.paging = True

    def _get_pseudo_margins(self):
        return [
            self.extra_space[0],
            self.extra_space[1],
            self.extra_space[2] + self.y,
            self.extra_space[3],
        ]
        # return [
        #    self.extra_space[0],
        #    self.extra_space[1],
        #    self.extra_space[2],
        #    self.extra_space[3],
        # ]

    def get_client_height(self):
        """Calculate the client height for rendering."""
        if not self.dc_page:
            self.render_new_page()
        return self.dc_page.dy

    def close(self):
        """Finalize rendering and clean up."""
        if self.parser.parse_only:
            return
        if self.atom_list:
            self.child_ready_to_render(None)
        if self.footer:
            self.print_footer()
        w, h = self.dc.get_max_sizes()
        self._maxwidth = (
            max(w, self._maxwidth) + self.extra_space[0] + self.extra_space[1]
        )
        self._maxheight = (
            max(h, self._maxheight) + self.extra_space[2] + self.extra_space[3]
        )
        self.parser.set_max_rendered_size(self._maxwidth, self._maxheight)

    def render_new_page(self):
        """Render a new page."""
        if self.new_page != 0 and self.footer:
            self.print_footer()
        if self.new_page != 0 and self.dc.paging:
            self.page += 1
            self.dc.start_page()
        self.dc_page = self.dc
        for r in self.render_helpers:
            self.dc_page = r.render(self.dc_page)
        if self.dc.paging:
            self.y = 0
            self.new_page = 1
            self.print_header()

    def render_atom_list(self):
        """Render the list of atomic elements."""
        if self.atom_list:
            dy = InlineElements.calc_height(self)
            if dy > 0:
                dy -= self.extra_space[2] + self.extra_space[3]
            if self.dc.paging and dy > self.height - self.footer_height - self.y:
                self.render_new_page()
            render_helpers = self.render_helpers
            self.render_helpers = []
            self.render(self.dc_page.subdc(0, self.y, self.width, dy))
            self.render_helpers = render_helpers
            self.new_page = 2
            self.y += dy
            self.atom_list = None
            if self.y > self._maxheight:
                self._maxheight = self.y

    def child_ready_to_render(self, child):
        """Handle child elements ready for rendering."""
        if self.dc_info.dc.handle_html_directly:
            return super().child_ready_to_render(child)
        if self.parser.parse_only:
            return
        if self.dc:
            if self.new_page == 0:
                self.render_new_page()
            self.render_atom_list()
            if child:
                cont = True
                while cont:
                    width, min_width, max_width = child.get_width()
                    w = (
                        max_width
                        if max_width >= 0 and max_width < self.get_client_width()[0]
                        else (
                            min_width
                            if min_width >= 0 and min_width > self.get_client_width()[0]
                            else self.get_client_width()[0]
                        )
                    )
                    child.set_width(w)
                    if w + self.extra_space[0] + self.extra_space[1] > self._maxwidth:
                        self._maxwidth = w + self.extra_space[0] + self.extra_space[1]
                    dy = child.get_height()
                    child.set_height(dy)
                    if (
                        not self.dc.paging
                        or dy
                        <= self.height
                        - self.footer_height
                        - self.y
                        - self.extra_space[2]
                        - self.extra_space[3]
                        or self.new_page != 2
                    ):
                        dy, cont = child.render(
                            self.dc_page.subdc(
                                0, self.y, self.get_client_width()[0], dy
                            )
                        )
                        self.new_page = 2
                        if dy > 0:
                            self.y += dy
                    else:
                        self.render_new_page()
                        cont = True
                        self.new_page = 1
                    if self.y > self._maxheight:
                        self._maxheight = self.y


register_tag_map("body", BodyTag)


class FormTag(BaseHtmlElemParser):
    """Handles the <form> tag in HTML, managing form fields and submissions."""

    def __init__(self, parent, parser, tag, attrs):
        super().__init__(parent, parser, tag, attrs)
        self.child_tags = parent.child_tags + ["table"]
        self.fields = None
        self.field_names = {}
        self.upload = None
        self.parent.reg_field = self.reg_field
        self.parent.get_fields = self.get_fields
        self.parent.gethref = self.gethref
        self.parent.set_upload = self.set_upload
        self.parent.get_upload = self.get_upload
        self.parent.form_obj = self

    def close(self):
        """Clean up form resources."""
        self.parent.form_obj = None

    def handle_data(self, data):
        """Handle data within the form."""
        pass

    def handle_starttag(self, parser, tag, attrs):
        """Handle start tags within the form."""
        obj = super().handle_starttag(parser, tag, attrs)
        if obj:
            obj.parent = self.parent
        return obj

    def reg_field(self, field):
        """Register a form field."""
        if field in self.field_names:
            self.field_names[field] += 1
            field2 = f"{field}__{self.field_names[field]}"
        else:
            self.field_names[field] = 1
            field2 = field
        if not field.startswith("_"):
            self.fields = f"{self.fields},{field2}" if self.fields else field2
        return field2

    def get_fields(self):
        """Get the form fields."""
        method = self.attrs.get("method", "GET")
        return f"{method}:{self.fields}" if self.fields else None

    def gethref(self):
        """Get the form action URL."""
        return self.attrs["action"]

    def set_upload(self, upload):
        """Set the upload file."""
        self.upload = upload

    def get_upload(self):
        """Get the upload file."""
        return self.upload


register_tag_map("form", FormTag)
