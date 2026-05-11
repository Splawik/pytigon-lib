"""
HTML content parsers for extracting structured data from HTML documents.

This module provides parsers for:
- Tables (:class:`SimpleTabParserBase`, :class:`SimpleTabParser`)
- Unordered lists / tree structures (:class:`TreeParser`)
- SchPage window layout (:class:`ShtmlParser`) – splits a page into
  header, footer, panel, body, and script fragments.
"""

from typing import Any, Dict, List, Optional, Tuple

from pytigon_lib.schparser.parser import (
    Parser,
    Elem,
    Script,
    content_tostring,
    tostring,
)
from pytigon_lib.schhtml.htmltools import Td
from pyquery import PyQuery as pq


class ExtList(list):
    """Extended list holding a table row with metadata.

    Attributes:
        row_id: Identifier from the ``row-id`` attribute of the ``<tr>``.
        class_attr: CSS class(es) from the ``class`` attribute.
    """

    row_id: int = 0
    class_attr: str = ""


class SimpleTabParserBase(Parser):
    """Extracts all ``<table>`` elements from HTML into :attr:`tables`.

    Each table is a list of rows, where each row is an :class:`ExtList`
    containing the text content of ``<th>`` and ``<td>`` cells.

    Subclasses may override :meth:`_preprocess` to transform cell content.
    """

    def __init__(self) -> None:
        super().__init__()
        self.tables: List[List[ExtList]] = []

    def _preprocess(self, td: Any) -> str:
        """Convert a table cell element to its string content.

        Args:
            td: An ElementTree ``<th>`` or ``<td>`` element.

        Returns:
            Stripped text/inner-HTML of the cell.
        """
        return content_tostring(td).strip()

    def feed(self, html_txt: str) -> None:
        """Parse HTML and populate :attr:`tables` with extracted table data.

        Args:
            html_txt: Raw HTML string.
        """
        self.init(html_txt)
        if self._tree is None:
            return
        for table_elem in self._tree.iterfind(".//table"):
            table: List[ExtList] = []
            for tr_elem in table_elem.iterfind(".//tr"):
                tr = ExtList()
                row_id = tr_elem.attrib.get("row-id")
                if row_id is not None:
                    tr.row_id = row_id
                class_attr = tr_elem.attrib.get("class")
                if class_attr is not None:
                    tr.class_attr = class_attr

                # Process header cells first, then data cells
                for th_elem in tr_elem.iterfind(".//th"):
                    tr.append(self._preprocess(th_elem))
                for td_elem in tr_elem.iterfind(".//td"):
                    tr.append(self._preprocess(td_elem))

                table.append(tr)
            self.tables.append(table)


class SimpleTabParser(SimpleTabParserBase):
    """Like :class:`SimpleTabParserBase` but wraps each cell in a :class:`Td` object.

    The :class:`Td` object preserves the original element's attributes
    alongside the text content.
    """

    def _preprocess(self, td: Any) -> Td:
        """Wrap cell content and attributes in a :class:`Td` instance.

        Args:
            td: An ElementTree ``<th>`` or ``<td>`` element.

        Returns:
            A :class:`Td` carrying the cell's text and attributes.
        """
        return Td(content_tostring(td).strip(), dict(td.attrib))


class TreeParser(Parser):
    """Parses nested ``<ul>`` / ``<li>`` structures into a tree.

    The result is stored in :attr:`list` as a nested structure::

        ["TREE", [
            ["item text", [... children ...], [... attributes ...]],
            ...
        ]]

    Where each ``<li>`` becomes a ``[text, children, attrs]`` triple.
    """

    def __init__(self) -> None:
        super().__init__()
        self.tree_parent: List[Any] = ["TREE", []]
        self.list: List[Any] = self.tree_parent
        self.stack: List[List[Any]] = []
        self._attr_buffer: List[Tuple[str, str]] = []
        self._data_enabled: bool = False

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, str]]) -> None:
        """Handle opening tags during tree crawling.

        Args:
            tag: Lowercased tag name.
            attrs: List of ``(name, value)`` attribute pairs.
        """
        if tag == "ul":
            self.stack.append(self.list)
            # Navigate into the children list of the current tree node
            self.list = self.list[-1][1]
            self._data_enabled = False
        elif tag == "li":
            self._data_enabled = True
            self.list.append(["", [], []])
            self._attr_buffer = list(attrs)
        else:
            # Accumulate attributes from other elements inside <li>
            self._attr_buffer.extend(attrs)

    def handle_endtag(self, tag: str) -> None:
        """Handle closing tags during tree crawling.

        Args:
            tag: Tag name.
        """
        if tag == "ul":
            if self.stack:
                self.list = self.stack.pop()
        elif tag == "li":
            if self.list:
                self.list[-1][2] = list(self._attr_buffer)
            self._attr_buffer = []
        self._data_enabled = False

    def handle_data(self, data: str) -> None:
        """Accumulate text content for the current ``<li>``.

        Args:
            data: Raw text data (whitespace on the right is stripped).
        """
        if self._data_enabled and self.list:
            self.list[-1][0] = self.list[-1][0] + data.rstrip(" \n")


class ShtmlParser(Parser):
    """Parser for SchPage windows – splits HTML into layout fragments.

    Extracts metadata from ``<meta>`` tags and divides the document into:
    body, header, footer, and panel regions. Each region is represented
    as an ``(Elem, Script)`` tuple.

    The selectors used for repartitioning are ``#header``, ``#footer``,
    and ``#panel``. Elements matching these are removed from the body.
    """

    def __init__(self) -> None:
        super().__init__()
        self.address: Optional[str] = None
        self._title: Optional[str] = None
        self._data: List[Any] = []
        self.var: Dict[str, Optional[str]] = {}
        self.schhtml: Optional[int] = None

    @staticmethod
    def _data_to_string(item: Optional[Any]) -> str:
        """Serialize a data fragment to a string.

        Args:
            item: An ElementTree element or None.

        Returns:
            String representation or ``""`` if *item* is None.
        """
        return tostring(item) if item is not None else ""

    @staticmethod
    def _script_to_string(item: Optional[Any]) -> str:
        """Extract the text content of a script fragment.

        Args:
            item: An ElementTree element (usually ``<script>``) or None.

        Returns:
            The element's ``.text`` or ``""`` if *item* is None.
        """
        return item.text if item is not None else ""

    def _reparent(self, selectors: Tuple[str, ...]) -> List[Optional[Any]]:
        """Extract and remove elements matching CSS selectors from the tree.

        For each selector, returns a pair ``[element, script_element]``.
        An empty selector means "the remainder of the document".

        Args:
            selectors: A tuple of CSS selectors (may contain empty strings).

        Returns:
            A flat list of ``[elem, script, elem, script, ...]``.
        """
        result: List[Optional[Any]] = []
        doc = pq(self._tree)

        for selector in selectors:
            if selector:
                match = doc(selector)
            else:
                match = doc

            # Extract <script> children before removal
            scripts = match("script")
            # Get the first matched element (or None)
            elem = match[0] if len(match) > 0 else None
            script_elem = scripts[0] if len(scripts) > 0 else None

            result.append(elem)
            result.append(script_elem)

            # Remove matched element from the document
            if selector and len(match) > 0:
                doc.remove(selector)

        return result

    def process(self, html_txt: str, address: Optional[str] = None) -> None:
        """Parse an HTML document and partition it into layout fragments.

        Args:
            html_txt: Raw HTML string.
            address: Optional address associated with the page.
        """
        self.address = address
        self.init(html_txt)

        if self._tree is None:
            return

        # Extract <meta> tag information
        for meta in self._tree.iterfind(".//meta"):
            name_attr = meta.attrib.get("name")
            content_attr = meta.attrib.get("content")
            if name_attr:
                name = name_attr.lower()
                if content_attr is not None:
                    if name == "schhtml":
                        try:
                            self.schhtml = int(content_attr)
                        except (ValueError, TypeError):
                            self.schhtml = None
                    else:
                        self.var[name] = content_attr
                else:
                    self.var[name] = None

        self._data = self._reparent(("", "#header", "#footer", "#panel"))

    @property
    def title(self) -> str:
        """The content of the ``<title>`` tag (lazy, cached)."""
        if self._title is None:
            if self._tree is not None:
                title_elem = self._tree.findtext(".//title")
                self._title = title_elem.strip() if title_elem else ""
            else:
                self._title = ""
        return self._title

    # ------------------------------------------------------------------
    # Fragment accessors – each returns ``(Elem, Script)`` or None if
    # the fragment was not present in the source document.
    # ------------------------------------------------------------------

    def get_body(self) -> Tuple[Optional[Elem], Optional[Script]]:
        """Return the body fragment (remainder after repartitioning)."""
        if len(self._data) < 2:
            return (None, None)
        return (Elem(self._data[0]), Script(self._data[1]))

    def get_header(self) -> Tuple[Optional[Elem], Optional[Script]]:
        """Return the ``#header`` fragment."""
        if len(self._data) < 4:
            return (None, None)
        return (Elem(self._data[2]), Script(self._data[3]))

    def get_footer(self) -> Tuple[Optional[Elem], Optional[Script]]:
        """Return the ``#footer`` fragment."""
        if len(self._data) < 6:
            return (None, None)
        return (Elem(self._data[4]), Script(self._data[5]))

    def get_panel(self) -> Tuple[Optional[Elem], Optional[Script]]:
        """Return the ``#panel`` fragment."""
        if len(self._data) < 8:
            return (None, None)
        return (Elem(self._data[6]), Script(self._data[7]))

    def get_body_attrs(self) -> Dict[str, str]:
        """Return attributes of the ``<body>`` element.

        Returns:
            Attribute dictionary, or an empty dict if no body exists.
        """
        if self._tree is None:
            return {}
        body = self._tree.find(".//body")
        return dict(body.attrib) if body is not None else {}


# ------------------------------------------------------------------
# Quick smoke-test when the module is run directly.
# ------------------------------------------------------------------
if __name__ == "__main__":
    try:
        with open("test.html", "rt") as f:
            data = f.read()
        mp = ShtmlParser()
        mp.process(data)
        if "TARGET" in mp.var:
            print("HEJ:", mp.var["TARGET"])
            print("<title***>", mp.title, "</title***>")
            header = mp.get_header()
            body = mp.get_body()
            footer = mp.get_footer()
            panel = mp.get_panel()
            print("<header***>", str(header[0]) if header[0] else "", "</header***>")
            print("<BODY***>", str(body[0]) if body[0] else "", "</BODY***>")
            print("<footer***>", str(footer[0]) if footer[0] else "", "</footer***>")
            print("<panel***>", str(panel[0]) if panel[0] else "", "</panel***>")
    except FileNotFoundError:
        print("Error: test.html not found.")
    except Exception as e:
        print(f"An error occurred: {e}")
