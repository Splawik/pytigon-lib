"""
This module provides classes and functions to parse and handle HTML content.

Classes:
    Parser: A class to parse HTML content and handle tags and data.
    Elem: A class to represent an HTML element.
    Script: A class to represent a script element.

Functions:
    tostring(elem: etree.Element) -> str: Convert an element to a string representation.
    content_tostring(elem: etree.Element) -> str: Convert the content of an element to a string.
"""

import io
import re
from typing import Optional, Union

try:
    from lxml import etree

    LXML = True
except ImportError:
    import xml.etree.ElementTree as etree
    from naivehtmlparser import NaiveHTMLParser

    LXML = False


class Parser:
    """A class to parse HTML content and handle tags and data."""

    def __init__(self):
        self._tree: Optional[etree.Element] = None
        self._cur_elem: Optional[etree.Element] = None

    def get_starttag_text(self) -> str:
        """Generate the start tag text for the current element."""
        if self._cur_elem:
            attributes = " ".join(
                f'{key}="{value}"' if value else key
                for key, value in self._cur_elem.items()
            )
            return (
                f"<{self._cur_elem.tag} {attributes}>"
                if attributes
                else f"<{self._cur_elem.tag}>"
            )
        return ""

    def handle_starttag(self, tag: str, attrib: dict) -> None:
        """Handle the start tag of an element."""
        pass

    def handle_data(self, txt: str) -> None:
        """Handle the text data within an element."""
        pass

    def handle_endtag(self, tag: str) -> None:
        """Handle the end tag of an element."""
        pass

    def _crawl_tree(self, tree: etree.Element) -> None:
        """Recursively crawl through the HTML tree."""
        self._cur_elem = tree
        if isinstance(tree.tag, str):
            self.handle_starttag(tree.tag.lower(), tree.attrib)
            if tree.text:
                self.handle_data(tree.text)
            for node in tree:
                self._crawl_tree(node)
            self.handle_endtag(tree.tag)
        if tree.tail:
            self.handle_data(tree.tail)

    def crawl_tree(self, tree: etree.Element) -> None:
        """Start crawling the HTML tree."""
        self._tree = tree
        self._crawl_tree(self._tree)

    def from_html(self, html_txt: str) -> etree.Element:
        """Parse HTML text and return the root element."""
        if LXML:
            parser = etree.HTMLParser(
                remove_blank_text=True, remove_comments=True, remove_pis=True
            )
            return etree.parse(io.StringIO(html_txt), parser).getroot()
        else:
            parser = NaiveHTMLParser()
            root = parser.feed(html_txt)
            parser.close()
            return root

    def init(self, html_txt: Union[str, "Elem"]) -> None:
        """Initialize the parser with HTML text or an Elem object."""
        if isinstance(html_txt, Elem):
            self._tree = self.from_html("<html></html>")
            self._tree.append(html_txt.elem)
        else:
            try:
                self._tree = self.from_html(html_txt)
            except Exception as e:
                print(f"Error parsing HTML: {e}")
                self._tree = None

    def feed(self, html_txt: Union[str, "Elem"]) -> None:
        """Feed HTML text to the parser and start crawling."""
        self.init(html_txt)
        if self._tree is not None and len(self._tree) > 0:
            self._crawl_tree(self._tree)

    def close(self) -> None:
        """Close the parser and reset the tree."""
        self._tree = None


def tostring(elem: etree.Element) -> str:
    """Convert an element to a string representation."""
    if LXML:
        return etree.tostring(
            elem, encoding="unicode", method="html", pretty_print=True
        )
    else:
        return etree.tostring(elem, encoding="unicode", method="html")


def content_tostring(elem: etree.Element) -> str:
    """Convert the content of an element to a string."""
    tab = []
    if elem.text:
        tab.append(elem.text)
    for pos in elem:
        tab.append(tostring(pos))
    if elem.tail:
        tab.append(elem.tail)
    return "".join(tab)


class Elem:
    """A class to represent an HTML element."""

    def __init__(self, elem: etree.Element, tostring_fun=tostring):
        self.elem = elem
        self._elem_txt: Optional[str] = None
        self._tostring_fun = tostring_fun

    def __str__(self) -> str:
        """Return the string representation of the element."""
        if self._elem_txt is None:
            self._elem_txt = (
                self._tostring_fun(self.elem) if self.elem is not None else ""
            )
        return self._elem_txt

    def __len__(self) -> int:
        """Return the length of the element's string representation."""
        if self._elem_txt is None:
            self._elem_txt = self._tostring_fun(self.elem)
        return len(self._elem_txt)

    def __bool__(self) -> bool:
        """Return True if the element exists, False otherwise."""
        return self.elem is not None

    @staticmethod
    def super_strip(s: str) -> str:
        """Strip and clean the string by removing extra spaces and newlines."""
        s = re.sub(r"(( )*(\\n)*)*", "", s)
        return s.strip()

    def tostream(
        self,
        output: Optional[io.StringIO] = None,
        elem: Optional[etree.Element] = None,
        tab: int = 0,
    ) -> io.StringIO:
        """Convert the element to a stream representation."""
        if elem is None:
            elem = self.elem
        if output is None:
            output = io.StringIO()
        if isinstance(elem.tag, str):
            output.write(" " * tab)
            output.write(elem.tag.lower())
            first = True
            for key, value in elem.attrib.items():
                if first:
                    output.write(" ")
                else:
                    output.write(",,,")
                output.write(key)
                output.write("=")
                if isinstance(value, str):
                    output.write(value.replace("\n", "\\n"))
                else:
                    output.write(str(value).replace("\n", "\\n"))
                first = False
            if elem.text:
                x = self.super_strip(elem.text.replace("\n", "\\n"))
                if x:
                    output.write("...")
                    output.write(x)
            output.write("\n")
            for node in elem:
                self.tostream(output, node, tab + 4)
        if elem.tail:
            x = self.super_strip(elem.tail.replace("\n", "\\n"))
            if x:
                output.write(" " * tab)
                output.write(".")
                output.write(x)
                output.write("\n")
        return output


class Script(Elem):
    """A class to represent a script element."""

    def __init__(self, elem: etree.Element, tostring_fun=content_tostring):
        super().__init__(elem, tostring_fun)
