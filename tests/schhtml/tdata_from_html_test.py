"""Regression tests for :func:`pytigon_lib.schhtml.htmlviewer.tdata_from_html`.

Table extraction must not create a PDF device context.  The old implementation
created ``PdfDc(calc_only=True)``, which made fpdf add all twelve TTF fonts and
decompile their whole ``glyf`` tables through fontTools.  Because calc_only
contexts never call ``output()``, fpdf's ``SubsetMap`` ``@cache`` pinned a full
font set (~47k ``Glyph`` objects, ~38 MB) per call.
"""

from pytigon_lib.schhtml import htmlviewer
from pytigon_lib.schhtml.basedc import BaseDc


def test_tdata_from_html_never_uses_pdf_dc(monkeypatch):
    """Any attempt to build a PDF context must fail loudly."""

    class _Boom:
        def __init__(self, *args, **kwargs):
            raise AssertionError("tdata_from_html must not create a PDF context")

    monkeypatch.setattr(htmlviewer, "PdfDc", _Boom)

    result = htmlviewer.tdata_from_html(
        "<html><body><table><tr><td>x</td></tr></table></body></html>", None
    )
    assert result is None


def test_tdata_from_html_uses_base_dc(monkeypatch):
    """The parser must run on a lightweight :class:`BaseDc`."""
    captured = {}

    class _StubParser:
        tdata_tab = []

        def __init__(self, dc=None, parse_only=False, **kwargs):
            captured["dc"] = dc

        def set_http_object(self, http):
            pass

        def feed(self, html):
            pass

        def close(self):
            pass

    monkeypatch.setattr(htmlviewer, "HtmlViewerParser", _StubParser)

    assert htmlviewer.tdata_from_html("<table></table>", None) is None
    assert isinstance(captured["dc"], BaseDc)
    assert not isinstance(captured["dc"], htmlviewer.PdfDc)
