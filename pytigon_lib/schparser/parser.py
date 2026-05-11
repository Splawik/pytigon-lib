"""
HTML parsing module for Pytigon.

Provides a base parser class and utility functions for parsing HTML content,
with support for both lxml and Python's standard ElementTree as fallback.

Classes:
    Parser: Base class for HTML parsing with tree crawling.
    Elem: Wrapper for HTML elements with string conversion utilities.
    Script: Specialized Elem for script elements.

Functions:
    tostring(elem) -> str: Serialize an element to HTML string.
    content_tostring(elem) -> str: Serialize inner content of an element.
"""

import io
import re
from typing import Any, Callable, Dict, List, Optional, Union

try:
    from lxml import etree

    _LXML_AVAILABLE = True
except ImportError:
    import xml.etree.ElementTree as etree
    from naivehtmlparser import NaiveHTMLParser

    _LXML_AVAILABLE = False


class Parser:
    """Base HTML parser with tree crawling and tag/data handling.

    Subclasses override :meth:`handle_starttag`, :meth:`handle_data`,
    and :meth:`handle_endtag` to process HTML content.

    Attributes:
        _tree: The root element tree being parsed.
        _cur_elem: The current element during tree traversal.
    """

    def __init__(self) -> None:
        self._tree: Optional[etree.Element] = None
        self._cur_elem: Optional[etree.Element] = None

    def get_starttag_text(self) -> str:
        """Generate the opening tag string for the current element.

        Returns:
            String like ``<tagname attr="value">`` or ``<tagname>``.
        """
        if self._cur_elem is None:
            return ""
        attributes = " ".join(
            f'{key}="{value}"' if value else key
            for key, value in self._cur_elem.items()
        )
        if attributes:
            return f"<{self._cur_elem.tag} {attributes}>"
        return f"<{self._cur_elem.tag}>"

    def handle_starttag(self, tag: str, attrib: Dict[str, str]) -> None:
        """Handle a start tag during tree crawling.

        Override in subclasses to process opening tags.

        Args:
            tag: The tag name (lowercased).
            attrib: Dictionary of tag attributes.
        """
        pass

    def handle_data(self, txt: str) -> None:
        """Handle text data encountered during tree crawling.

        Override in subclasses to process text content.

        Args:
            txt: The text content (may include whitespace).
        """
        pass

    def handle_endtag(self, tag: str) -> None:
        """Handle a closing tag during tree crawling.

        Override in subclasses to process closing tags.

        Args:
            tag: The tag name.
        """
        pass

    def _crawl_tree(self, tree: etree.Element) -> None:
        """Recursively traverse an HTML element tree.

        Calls handle_starttag, handle_data, and handle_endtag
        for each node in depth-first order.

        Args:
            tree: The root element to traverse.
        """
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
        """Begin crawling an HTML element tree.

        Args:
            tree: The root element tree to crawl.
        """
        self._tree = tree
        self._crawl_tree(self._tree)

    @staticmethod
    def from_html(html_txt: str) -> etree.Element:
        """Parse raw HTML text into an element tree.

        Uses lxml when available, falling back to the bundled
        NaiveHTMLParser.

        Args:
            html_txt: Raw HTML string to parse.

        Returns:
            The root element of the parsed tree.

        Raises:
            ValueError: If the HTML cannot be parsed.
        """
        if _LXML_AVAILABLE:
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
        """Initialize the parser with HTML text or an Elem wrapper.

        Args:
            html_txt: Either a raw HTML string or an :class:`Elem` instance.

        Note:
            When an Elem is passed, it is wrapped inside a minimal
            ``<html>`` document for consistent tree handling.
        """
        if isinstance(html_txt, Elem):
            self._tree = self.from_html("<html></html>")
            self._tree.append(html_txt.elem)
        else:
            try:
                self._tree = self.from_html(html_txt)
            except Exception:
                self._tree = None

    def feed(self, html_txt: Union[str, "Elem"]) -> None:
        """Parse and crawl HTML content in one step.

        Equivalent to calling :meth:`init` followed by
        :meth:`_crawl_tree` on the result.

        Args:
            html_txt: Raw HTML string or :class:`Elem` instance.
        """
        self.init(html_txt)
        if self._tree is not None and len(self._tree) > 0:
            self._crawl_tree(self._tree)

    def close(self) -> None:
        """Reset the parser, clearing the internal tree."""
        self._tree = None


def tostring(elem: etree.Element) -> str:
    """Serialize an element to its HTML string representation.

    Args:
        elem: An ElementTree element.

    Returns:
        HTML string. Pretty-printed when lxml is available.
    """
    if _LXML_AVAILABLE:
        return etree.tostring(
            elem, encoding="unicode", method="html", pretty_print=True
        )
    return etree.tostring(elem, encoding="unicode", method="html")


def content_tostring(elem: etree.Element) -> str:
    """Extract the inner text and HTML content of an element as a string.

    Concatenates the element's own text, the serialized representation
    of each child element, and the element's tail text.

    Args:
        elem: An ElementTree element.

    Returns:
        Concatenated string of all content within the element.
    """
    parts: List[str] = []
    if elem.text:
        parts.append(elem.text)
    for child in elem:
        parts.append(tostring(child))
    if elem.tail:
        parts.append(elem.tail)
    return "".join(parts)


class Elem:
    """Wrapper around an ElementTree element with string conversion.

    Provides lazy string conversion, boolean testing (non-None element),
    and a debug-oriented tree stream representation.

    Attributes:
        elem: The underlying ElementTree element (may be None).
    """

    def __init__(
        self,
        elem: Optional[etree.Element],
        tostring_fun: Callable[[Optional[etree.Element]], str] = tostring,
    ) -> None:
        """Initialize with an element and optional serialization function.

        Args:
            elem: An ElementTree element or None.
            tostring_fun: Function to convert the element to a string.
        """
        self.elem: Optional[etree.Element] = elem
        self._elem_txt: Optional[str] = None
        self._tostring_fun = tostring_fun

    def __str__(self) -> str:
        """Return the string representation of the element (lazy computed)."""
        if self._elem_txt is None:
            self._elem_txt = (
                self._tostring_fun(self.elem) if self.elem is not None else ""
            )
        return self._elem_txt

    def __len__(self) -> int:
        """Return the character length of the element's string representation."""
        if self._elem_txt is None:
            self._elem_txt = (
                self._tostring_fun(self.elem) if self.elem is not None else ""
            )
        return len(self._elem_txt)

    def __bool__(self) -> bool:
        """Return True if the wrapped element is not None."""
        return self.elem is not None

    @staticmethod
    def super_strip(s: str) -> str:
        """Clean a string by collapsing whitespace and removing literal ``\\n``.

        Converts sequences of spaces and literal backslash-n into a single
        space, then strips leading/trailing whitespace.

        Args:
            s: The input string to clean.

        Returns:
            Stripped string with collapsed whitespace.
        """
        if not s:
            return ""
        # Collapse runs of spaces, tabs, and literal '\n' sequences
        s = re.sub(r"[\t ]+", " ", s)
        s = re.sub(r"(\\n\s*)+", " ", s)
        return s.strip()

    def tostream(
        self,
        output: Optional[io.StringIO] = None,
        elem: Optional[etree.Element] = None,
        tab: int = 0,
    ) -> io.StringIO:
        """Write a human-readable tree representation to a stream.

        Useful for debugging HTML structure.

        Args:
            output: An existing StringIO buffer, or None to create one.
            elem: Element to serialize; defaults to :attr:`self.elem`.
            tab: Indentation level (in spaces).

        Returns:
            The StringIO buffer containing the tree representation.
        """
        if elem is None:
            elem = self.elem
        if elem is None:
            return output or io.StringIO()
        if output is None:
            output = io.StringIO()

        if isinstance(elem.tag, str):
            indent = " " * tab
            output.write(indent)
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
                cleaned = self.super_strip(elem.text.replace("\n", "\\n"))
                if cleaned:
                    output.write("...")
                    output.write(cleaned)

            output.write("\n")
            for node in elem:
                self.tostream(output, node, tab + 4)

        if elem.tail:
            cleaned = self.super_strip(elem.tail.replace("\n", "\\n"))
            if cleaned:
                output.write(" " * tab)
                output.write(".")
                output.write(cleaned)
                output.write("\n")

        return output


class Script(Elem):
    """Specialized Elem for ``<script>`` elements.

    Uses :func:`content_tostring` for serialization instead of
    :func:`tostring`, so the ``<script>`` tags are omitted and only
    the inner content is returned.
    """

    def __init__(
        self,
        elem: Optional[etree.Element],
        tostring_fun: Callable[[Optional[etree.Element]], str] = content_tostring,
    ) -> None:
        super().__init__(elem, tostring_fun)
