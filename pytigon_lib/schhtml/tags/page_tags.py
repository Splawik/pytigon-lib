from pytigon_lib.schhtml.basehtmltags import BaseHtmlElemParser, register_tag_map
import io


class Page(BaseHtmlElemParser):
    """Represents a page element in the HTML structure."""

    def __init__(self, parent, parser, tag, attrs):
        super().__init__(parent, parser, tag, attrs)
        self.child_tags = ["header", "footer"]
        self.body = parent

    def data_from_child(self, child, data):
        """Pass data from child elements to the parent."""
        self.parent.data_from_child(child, data)

    def close(self):
        """Handle closing of the page element."""
        pass

    def finish(self):
        """Notify the parent that the page has changed."""
        self.body.page_changed()


class NewPage(BaseHtmlElemParser):
    """Represents a new page element in the HTML structure."""

    def __init__(self, parent, parser, tag, attrs):
        super().__init__(parent, parser, tag, attrs)
        self.body = parent

    def close(self):
        """Handle closing of the new page element."""
        pass

    def finish(self):
        """Render a new page."""
        self.body.render_new_page()


class HeaderFooter(BaseHtmlElemParser):
    """Represents header and footer elements in the HTML structure."""

    def __init__(self, parent, parser, tag, attrs):
        super().__init__(parent, parser, tag, attrs)
        self.data = io.StringIO()

    def handle_starttag(self, parser, tag, attrs):
        """Handle the start tag of child elements."""
        self.data.write(f"<{tag}")
        for pos, value in attrs.items():
            if value is not None:
                self.data.write(f' {pos}="{value}"')
            else:
                self.data.write(f" {pos}")
        self.data.write(">")
        return None

    def handle_endtag(self, tag):
        """Handle the end tag of child elements."""
        if tag == self.tag:
            self.parent.data_from_child(self, self.data)
            return self.parent
        else:
            self.data.write(f"</{tag}>")
            return self

    def handle_data(self, data):
        """Handle data within the element."""
        self.data.write(data)

    def close(self):
        """Handle closing of the header/footer element."""
        pass


# Register the custom tags
register_tag_map("page", Page)
register_tag_map("header", HeaderFooter)
register_tag_map("footer", HeaderFooter)
register_tag_map("newpage", NewPage)
