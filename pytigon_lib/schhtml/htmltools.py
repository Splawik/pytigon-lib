from pytigon_lib.schparser.parser import Parser
from urllib.request import urlopen
from urllib.error import URLError


def superstrip(s):
    """Remove extra whitespace from the string."""
    f = (16, 8, 4, 2)
    s2 = s.replace("\n", " ").replace("\r", " ").replace("\t", " ")
    for pos in f:
        while True:
            oldlen = len(s2)
            s2 = s2.replace(" " * pos, " ")
            if len(s2) == oldlen:
                break
    return s2.strip()


class HtmlModParser(Parser):
    """Parser for modifying HTML content."""

    def __init__(self, url=None):
        super().__init__()
        if url:
            try:
                req = urlopen(url)
                self.feed(req.read().decode("utf-8"))
            except URLError as e:
                raise ValueError(f"Failed to fetch URL: {e}")


class HtmlProxyParser(Parser):
    """Proxy parser for handling HTML tags."""

    def __init__(self, tag):
        super().__init__()
        self.tag_obj = tag
        self.parser = tag.parser
        self.org_tag_parser = self.parser.tag_parser
        self.parser.tag_parser = tag
        self.org_state = tag.dc.state()
        tag.dc.restore_state(tag.base_state)

    def handle_starttag(self, tag, attrs):
        return self.parser.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        return self.parser.handle_endtag(tag)

    def handle_data(self, data):
        return self.parser.handle_data(data)

    def feed(self, html_txt):
        _tree = self._tree
        _cur_elem = self._cur_elem
        _header = self.tag_obj.header
        _footer = self.tag_obj.footer
        self.tag_obj.header = ""
        self.tag_obj.footer = ""
        super().feed(html_txt)
        self.tag_obj.header = _header
        self.tag_obj.footer = _footer
        self._tree = _tree
        self._cur_elem = _cur_elem

    def close(self):
        self.parser.tag_parser = self.org_tag_parser
        self.tag_obj.dc.restore_state(self.org_state)


class Td:
    """Represents a table data cell."""

    def __init__(self, data, attrs=None, children=None):
        self.data = data
        self.attrs = attrs if attrs is not None else {}
        self.children = children

    @property
    def attr(self):
        return ""

    def __repr__(self):
        return f"Td: {self.data}"
