from pytigon_lib.schhtml.basehtmltags import BaseHtmlElemParser, register_tag_map
from .tags.block_tags import *
from .tags.table_tags import *
from .tags.p_tags import *
from .tags.css_tags import *
from .tags.atom_tags import *
from .tags.page_tags import *
from .tags.extra_tags import *


class HtmlTag(BaseHtmlElemParser):
    """Represents the HTML tag in the document."""

    def __init__(self, parent, parser, tag, attrs):
        """Initialize the HTML tag with default attributes."""
        super().__init__(parent, parser, tag, attrs)
        self.child_tags = ["head", "body", "script"]
        self.width = 2480
        self.height = 3508
        self.y = 0
        self.dc = None
        self.attrs = {
            "color": "#000",
            "font-family": "sans-serif",
            "font-size": "100%",
            "font-style": "normal",
            "font-weight": "normal",
            "text-decoration": "none",
        }

    def handle_data(self, data):
        """Handle data within the HTML tag."""
        pass

    def close(self):
        """Close the HTML tag."""
        super().close()

    def set_dc(self, dc):
        """Set the drawing context and update width and height."""
        try:
            self.width, self.height = dc.get_size()
            self.dc = dc
        except AttributeError as e:
            raise ValueError("Invalid drawing context provided.") from e


class HeaderTag(BaseHtmlElemParser):
    """Represents the HEAD tag in the document."""

    def __init__(self, parent, parser, tag, attrs):
        """Initialize the HEAD tag with child tags."""
        super().__init__(parent, parser, tag, attrs)
        self.child_tags = ["style", "link"]

    def close(self):
        """Close the HEAD tag."""
        pass


class CommentTag(BaseHtmlElemParser):
    """Represents a comment in the document."""

    def __init__(self, parent, parser, tag, attrs):
        """Initialize the comment tag."""
        super().__init__(parent, parser, tag, attrs)

    def handle_starttag(self, parser, tag, attrs):
        """Handle the start tag within the comment."""
        return None

    def close(self):
        """Close the comment tag."""
        pass


# Register the tags with the parser
register_tag_map("html", HtmlTag)
register_tag_map("head", HeaderTag)
register_tag_map("comment", CommentTag)
