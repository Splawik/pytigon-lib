from pytigon_lib.schparser.parser import (
    Parser,
    content_tostring,
    Elem,
    Script,
    tostring,
)
from pytigon_lib.schhtml.htmltools import Td
from pyquery import PyQuery as pq


class ExtList(list):
    """Extended list class with additional attributes for table rows."""

    row_id = 0
    class_attr = ""


class SimpleTabParserBase(Parser):
    """Parses HTML for tables and saves found tables to self.tables."""

    def __init__(self):
        super().__init__()
        self.tables = []

    def _preprocess(self, td):
        """Preprocess table cell content."""
        return content_tostring(td).strip()

    def feed(self, html_txt):
        """Parse HTML and extract tables."""
        self.init(html_txt)
        for elem in self._tree.iterfind(".//table"):
            table = []
            for elem2 in elem.iterfind(".//tr"):
                tr = ExtList()
                if "row-id" in elem2.attrib:
                    tr.row_id = elem2.attrib["row-id"]
                if "class" in elem2.attrib:
                    tr.class_attr = elem2.attrib["class"]

                for elem3 in elem2.iterfind(".//th"):
                    tr.append(self._preprocess(elem3))
                for elem3 in elem2.iterfind(".//td"):
                    tr.append(self._preprocess(elem3))
                table.append(tr)
            self.tables.append(table)


class SimpleTabParser(SimpleTabParserBase):
    """Like SimpleTabParserBase but saves table cells as Td objects."""

    def _preprocess(self, td):
        """Preprocess table cell content into Td objects."""
        return Td(content_tostring(td).strip(), td.attrib)


class TreeParser(Parser):
    """Parses HTML for unordered lists (ul) and saves the structure to self.list."""

    def __init__(self):
        super().__init__()
        self.tree_parent = [["TREE", []]]
        self.list = self.tree_parent
        self.stack = []
        self.attr_to_li = []
        self.enable_data_read = False

    def handle_starttag(self, tag, attrs):
        """Handle start tags."""
        self.attr_to_li += attrs
        if tag == "ul":
            self.stack.append(self.list)
            self.list = self.list[-1][1]
            self.enable_data_read = False
        elif tag == "li":
            self.enable_data_read = True
            self.list.append(["", [], []])
            self.attr_to_li = []

    def handle_endtag(self, tag):
        """Handle end tags."""
        if tag == "ul":
            self.list = self.stack.pop()
        if tag == "li":
            self.list[-1][2] = self.attr_to_li
            self.attr_to_li = []
        self.enable_data_read = False

    def handle_data(self, data):
        """Handle data within tags."""
        if self.enable_data_read:
            self.list[-1][0] = self.list[-1][0] + data.rstrip(" \n")


class ShtmlParser(Parser):
    """Parser for SchPage window. Divides the page into parts: header, footer, panel, body, and script."""

    def __init__(self):
        super().__init__()
        self.address = None
        self._title = None
        self._data = None
        self.var = {}
        self.schhtml = None

    def _data_to_string(self, id):
        """Convert data to string."""
        return tostring(self._data[id]) if self._data[id] is not None else ""

    def _script_to_string(self, id):
        """Convert script to string."""
        return self._data[id].text if self._data[id] is not None else ""

    def _reparent(self, selectors):
        """Reparent elements based on selectors."""
        ret = []
        d = pq(self._tree)

        for selector in selectors:
            tmp = d(selector) if selector else d
            scripts = tmp("script")
            if scripts:
                tmp.remove("script")
            ret.append(tmp[0] if tmp else None)
            ret.append(scripts[0] if scripts else None)
            if selector and tmp:
                d.remove(selector)
        return ret

    def process(self, html_txt, address=None):
        """Process HTML content."""
        self.address = address
        self.init(html_txt)
        for elem in self._tree.iterfind(".//meta"):
            if "name" in elem.attrib:
                name = elem.attrib["name"].lower()
                if "content" in elem.attrib:
                    if name == "schhtml":
                        self.schhtml = int(elem.attrib["content"])
                    else:
                        self.var[name] = elem.attrib["content"]
                else:
                    self.var[name] = None
        self._data = self._reparent(("", "#header", "#footer", "#panel"))

    @property
    def title(self):
        """Get the title of the HTML document."""
        if not self._title:
            try:
                self._title = self._tree.findtext(".//title").strip()
            except AttributeError:
                self._title = ""
        return self._title

    def get_body(self):
        """Get body fragment."""
        return (Elem(self._data[0]), Script(self._data[1]))

    def get_header(self):
        """Get header fragment."""
        return (Elem(self._data[2]), Script(self._data[3]))

    def get_footer(self):
        """Get footer fragment."""
        return (Elem(self._data[4]), Script(self._data[5]))

    def get_panel(self):
        """Get panel fragment."""
        return (Elem(self._data[6]), Script(self._data[7]))

    def get_body_attrs(self):
        """Get body attributes."""
        body = self._tree.find(".//body")
        return body.attrib if body is not None else {}


if __name__ == "__main__":
    try:
        with open("test.html", "rt") as f:
            data = f.read()
        mp = ShtmlParser()
        mp.process(data)
        if "TARGET" in mp.var:
            print("HEJ:", mp.var["TARGET"])
            print("<title***>", mp.title, "</title***>")
            print("<header***>", mp.get_header()[0].getvalue(), "</header***>")
            print("<BODY***>", mp.get_body()[0].getvalue(), "</BODY***>")
            print("<footer***>", mp.get_footer()[0].getvalue(), "</footer***>")
            print("<panel***>", mp.get_panel()[0].getvalue(), "</panel***>")
    except FileNotFoundError:
        print("Error: test.html not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
