from pytigon_lib.schhtml.basehtmltags import BaseHtmlElemParser, register_tag_map
from django.contrib.staticfiles import finders


class Css(BaseHtmlElemParser):
    """Load CSS definitions from STYLE tag."""

    def __init__(self, parent, parser, tag, attrs):
        super().__init__(parent, parser, tag, attrs)

    def close(self):
        """Parse CSS definitions from the collected data."""
        css_content = "".join(self.data)
        if css_content:
            self.parser.css.parse_str(css_content)


register_tag_map("style", Css)


class CssLink(BaseHtmlElemParser):
    """Load CSS definitions from LINK tag."""

    def __init__(self, parent, parser, tag, attrs):
        super().__init__(parent, parser, tag, attrs)

    def close(self):
        """Load CSS definitions from the external CSS file."""
        href = self.attrs.get("href")
        if not href or ".ico" in href:
            return
        if href:
            http = self.parser.get_http_object()
            try:
                response = http.get(self, href)
                if response.ret_code == 200:
                    self.parser.css.parse_str(response.str())
            except Exception as e:
                print(f"Failed to load CSS from {href}: {e}")
        else:
            print(f"Failed to load CSS from {href}: file not found")


register_tag_map("link", CssLink)
