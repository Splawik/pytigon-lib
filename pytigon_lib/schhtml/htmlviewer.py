"""Module contains classes for rendering HTML content."""

import sys
import traceback
import os
import io
from tempfile import NamedTemporaryFile

from pytigon_lib.schhtml.htmltools import HtmlModParser
from pytigon_lib.schhtml.html_tags import HtmlTag
from pytigon_lib.schhtml.basedc import NullDc, BaseDc
from pytigon_lib.schhtml.css import Css
from pytigon_lib.schhtml.basehtmltags import get_tag_preprocess_map
from pytigon_lib.schhttptools.httpclient import HttpClient
from pytigon_lib.schhtml.pdfdc import PdfDc

ALIAS_TAG = {
    "em": "i",
    "strong": "b",
}


class BaseRenderingLib:
    @staticmethod
    def accept(html, stream_type="pdf", base_url=None, info=None):
        return False

    @staticmethod
    def render(
        html,
        output_stream=None,
        css=None,
        width=595,
        height=842,
        stream_type="pdf",
        base_url=None,
        info=None,
    ):
        pass


RENDERING_LIB = None


def set_rendering_lib(rendering_lib):
    global RENDERING_LIB
    RENDERING_LIB = rendering_lib


INIT_CSS_STR_BASE = """
    body {font-family:sans-serif;font-size:100%; padding:2;}
    table {border:5;vertical-align:top; padding:2;}
    td table { padding: 2; }
    th {border:5; cellpadding:2;}
    td {border:5; vertical-align:top; cellpadding:2;}
    strong,b {font-weight:bold;}
    p { cellpadding:5; border:1; width:100%; align: left; }
    h1 {font-size:300%; font-weight: bold; cellpadding:12;}
    h2 {font-size:240%; font-weight: bold; cellpadding:10;}
    h3 {font-size:190%; font-weight: bold; cellpadding:8;}
    h4 {font-size:150%; font-weight: bold; cellpadding:6;}
    h5 {font-size:120%; font-weight: bold; cellpadding:4;}
    h6 {font-size:100%; font-weight: bold; cellpadding:2;}
    a { color:#0000ff; text-decoration: underline; }
    ul {border:0;}
    li {cellpadding:5; width:93%-60; }
    dt {font-weight:bold; width:45%;}
    dd {width:45%; cellpadding:10; }
    calc { cellpadding:5; border:1; width:100%; }
"""


class HtmlViewerParser(HtmlModParser):
    """HTML renderer."""

    CSS_TYPE_STANDARD = 0
    CSS_TYPE_INDENT = 1

    def __init__(
        self,
        dc=None,
        dc_info=None,
        base_url=None,
        url=None,
        calc_only=False,
        parse_only=False,
        init_css_str=None,
        css_type=CSS_TYPE_STANDARD,
        use_tag_maps=True,
    ):
        """Initialize the HTML viewer parser."""
        self.tag_parser = None
        self.url = url
        self.base_url = base_url
        self.parse_only = parse_only
        self.use_tag_maps = use_tag_maps
        self.obj_id_dict = {}
        self.obj_action_dict = {}
        self.parent_window = None
        self._max_width = 0
        self._max_height = 0
        self.lp = 1
        self.table_lp = 0
        self.http = None
        self.tdata_tab = []
        self.debug = False

        self.calc_only = calc_only or parse_only
        self.dc = dc if dc else BaseDc()
        if self.calc_only:
            self.dc = NullDc(self.dc)

        self.dc_info = dc_info if dc_info else self.dc.get_dc_info()
        self.css = Css()
        if init_css_str:
            if init_css_str.startswith("@"):
                with open(
                    os.path.join(os.path.dirname(__file__), "icss", init_css_str[1:])
                ) as f:
                    init_css_str = f.read()
                    css_type = "icss"
            if css_type == self.CSS_TYPE_STANDARD:
                self.css.parse_str(init_css_str)
            else:
                self.css.parse_indent_str(init_css_str)
        else:
            self.css.parse_str(INIT_CSS_STR_BASE)

        HtmlModParser.__init__(self, url)

    def register_tdata(self, tdata, tag, attrs):
        """Register table data."""
        self.tdata_tab.append((tdata, tag, attrs))

    def set_http_object(self, http):
        """Set HTTP connector."""
        self.http = http

    def get_http_object(self):
        """Get HTTP connector."""
        if not self.http:
            self.http = HttpClient(self.base_url)
        return self.http

    def set_max_rendered_size(self, width, height):
        """Set maximum rendered size."""
        self._max_width = width
        self._max_height = height

    def get_max_rendered_size(self):
        """Get maximum rendered size."""
        return (self._max_width, self._max_height)

    def set_parent_window(self, win):
        """Set parent window."""
        self.parent_window = win

    def get_parent_window(self):
        """Get parent window."""
        return self.parent_window

    def reg_id_obj(self, id, dc, obj):
        """Register object by ID."""
        self.obj_id_dict[id] = obj
        obj.last_rendered_dc = dc
        obj.rendered_rects.append((dc.x, dc.y, dc.dx, dc.dy))

    def reg_action_obj(self, action, dc, obj):
        """Register object by action."""
        if action in self.obj_action_dict:
            self.obj_action_dict[action].append(obj)
        else:
            self.obj_action_dict[action] = [obj]
        obj.last_rendered_dc = dc
        obj.rendered_rects.append((dc.x, dc.y, dc.dx, dc.dy))

    def handle_starttag(self, tag, attrs):
        """Handle start tag."""
        self._handle_starttag(tag, attrs)

    def _handle_starttag(self, tag, attrs):
        """Internal method to handle start tag."""
        tag = ALIAS_TAG.get(tag, tag)
        try:
            if "style" in attrs:
                for s in attrs["style"].split(";"):
                    s2 = s.split(":")
                    if len(s2) == 2:
                        attrs[s2[0].lower()] = s2[1]

            if "class" in attrs:
                classes = attrs["class"].split(" ")
                attrs["class"] = classes[0]
                attrs["classes"] = attrs["class"]

            tmap = get_tag_preprocess_map()
            tag2 = tag.lower()
            if self.use_tag_maps:
                handler = tmap.get_handler(tag)
            else:
                handler = None
            if handler:
                attrs["_tag"] = tag
                (tag2, attrs) = handler(self.tag_parser, attrs)

            if self.tag_parser:
                obj = self.tag_parser.handle_starttag(self, tag2, attrs)
                if self.debug:
                    self.print_obj(obj, True)
                if obj:
                    obj.close_tag = tag
                    if obj.sys_id < 0:
                        obj.sys_id = self.lp
                        self.lp += 1
                    self.tag_parser = obj
                    self.tag_parser.set_dc_info(self.dc_info)
                    self.dc.annotate("start_tag", {"element": obj})
            else:
                if tag.lower() == "html":
                    self.tag_parser = HtmlTag(None, self, tag.lower(), attrs)
                    self.tag_parser.set_dc(self.dc)
        except Exception as e:
            traceback.print_exc()

    def handle_startendtag(self, tag, attrs):
        """Handle start-end tag."""
        self._handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag):
        """Handle end tag."""
        tag = ALIAS_TAG.get(tag, tag)
        try:
            if self.tag_parser:
                tag_parser = self.tag_parser
                obj = self.tag_parser.handle_endtag(tag.lower())
                if self.debug and obj != tag_parser:
                    self.print_obj(tag_parser, False)
                self.tag_parser = obj
                tag_parser.finish()
                self.dc.annotate("end_tag", {"element": tag_parser})
        except Exception as e:
            traceback.print_exc()
        if tag.lower() in ("table", "tdata"):
            self.table_lp += 1

    def handle_data(self, data):
        """Handle data."""
        try:
            if self.tag_parser:
                self.tag_parser.handle_data(data)
        except Exception as e:
            traceback.print_exc()

    def close(self):
        """Close the device context."""
        if self.dc:
            self.dc.end_document()
            self.dc.close()

    def get_max_sizes(self):
        """Get maximum sizes."""
        sizes = self.dc.get_max_sizes()
        sizes2 = self.get_max_rendered_size()
        return (max(sizes[0], sizes2[0]), max(sizes[1], sizes2[1]))

    def print_obj(self, obj, start=True):
        """Print object."""
        if obj:
            tab = -1
            parent = obj
            while parent:
                tab += 1
                parent = parent.parent
            print(
                "|   " * tab,
                obj.tag,
                obj.attrs if start else "/",
                obj.tag,
                "(",
                obj.height,
                ")",
            )


def stream_from_html(
    html,
    output_stream=None,
    css=None,
    width=595,
    height=842,
    stream_type="pdf",
    base_url=None,
    info=None,
):
    """Render HTML string."""
    if RENDERING_LIB and RENDERING_LIB.accept(html, stream_type, base_url, info):
        return RENDERING_LIB.render(
            html, output_stream, css, width, height, stream_type, base_url, info
        )

    if not isinstance(html, str):
        html = html.decode("utf-8")
    html2 = html if "<html" in html else f"<html><body>{html}</body></html>"

    width2, height2 = (
        (height, width)
        if "orientation:landscape" in html2 or "orientation: landscape" in html2
        else (width, height)
    )
    result = output_stream if output_stream else io.BytesIO()

    if stream_type == "pdf":
        result_buf = NamedTemporaryFile(delete=False)
        pdf_name = result_buf.name
        result_buf.close()

        def notify_callback(event_name, data):
            if event_name == 'end"':
                dc = data["dc"]
                dc.surf.set_subject(html2)

        dc = PdfDc(
            calc_only=False,
            width=width2,
            height=height2,
            output_name=pdf_name,
            notify_callback=notify_callback,
        )

    elif stream_type == "spdf":
        result_buf = NamedTemporaryFile(delete=False)
        pdf_name = result_buf.name
        result_buf.close()

        def notify_callback(event_name, data):
            if event_name == "end":
                dc = data["dc"]
                if dc.output_name:
                    dc.save(dc.output_name)
                else:
                    result_buf = NamedTemporaryFile(delete=False)
                    spdf_name = result_buf.name
                    result_buf.close()

                    dc.save(spdf_name)
                    with open(spdf_name, "rb") as f:
                        dc.ouput_stream.write(f.read())

        dc = PdfDc(
            calc_only=True,
            width=width2,
            height=height2,
            output_name=pdf_name,
            notify_callback=notify_callback,
        )

    else:
        dc = BaseDc(calc_only=False, width=width2, height=height2)

    dc.set_paging(True)
    p = HtmlViewerParser(dc=dc, calc_only=False, base_url=base_url)
    p.feed(html2.replace("&nbsp;", "»"))
    p.close()
    if stream_type == "pdf":
        with open(pdf_name, "rb") as f:
            result.write(f.read())
        os.unlink(pdf_name)
    else:
        with NamedTemporaryFile(delete=False) as f:
            name = f.name

        dc.end_page()
        dc.save(name)

        with open(name, "rb") as f:
            buf = f.read()
            result.write(buf)

        os.unlink(name)
    return result


def tdata_from_html(html, http):
    """Extract table data from HTML."""
    dc = PdfDc(calc_only=True, width=-1, height=-1)
    p = HtmlViewerParser(dc=dc, parse_only=True)
    p.set_http_object(http)
    p.feed(html)
    ctrls = p.tdata_tab
    p.close()
    tab = next((pos[0] for pos in ctrls if pos[1] == "ctrl-table"), None)
    return tab if tab and len(tab) > 0 else None
