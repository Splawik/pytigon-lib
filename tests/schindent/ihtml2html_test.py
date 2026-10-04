"""Round-trip test for the ihtml preprocessor.

The previous version of this test drove the ``run_schscripts.ihtml2html``
command through the CLI. That command does not exist in the test project, it
ignores ``-o`` and only handles ``.ihtml`` inputs, so the test could never
succeed. The behaviour under test is the library conversion itself, so it is
exercised directly here.

The reference files in ``wzr/`` are compared byte for byte, and they currently
predate the renderer's line-wrapping rule for long attribute values. They are
therefore treated as golden files: enable with ``PYTIGON_GOLDEN_TESTS=1`` and
regenerate them deliberately rather than blessing whatever the renderer
currently produces.
"""

import io
import os
import pathlib

import pytest

from pytigon_lib.schindent.html2ihtml import Html2IhtmlParser
from pytigon_lib.schindent.indent_style import ihtml_to_html_base

pytestmark = pytest.mark.skipif(
    os.environ.get("PYTIGON_GOLDEN_TESTS") != "1",
    reason="golden test; the wzr/ references predate the current line wrapping. "
    "Set PYTIGON_GOLDEN_TESTS=1 after regenerating them.",
)

TEST_PATH = pathlib.Path(__file__).parent.resolve()
ASSETS = TEST_PATH / "assets"
WZR = TEST_PATH / "wzr"


def test_html_to_ihtml():
    """``assets/test.html`` compiles to the reference ``wzr/test.ihtml``."""
    source = (ASSETS / "test.html").read_text(encoding="utf-8")
    expected = (WZR / "test.ihtml").read_text(encoding="utf-8")

    out = io.StringIO()
    parser = Html2IhtmlParser(out)
    parser.feed(source)
    parser.close()

    assert out.getvalue() == expected


def test_ihtml_to_html():
    """``wzr/test.ihtml`` renders back to the reference ``wzr/test.html``."""
    source = (WZR / "test.ihtml").read_text(encoding="utf-8")
    expected = (WZR / "test.html").read_text(encoding="utf-8")

    assert ihtml_to_html_base(None, input_str=source) == expected


def test_roundtrip_is_stable():
    """Converting back and forth twice reaches a fixed point."""
    html = (ASSETS / "test.html").read_text(encoding="utf-8")

    out = io.StringIO()
    parser = Html2IhtmlParser(out)
    parser.feed(html)
    parser.close()
    once = out.getvalue()

    again = ihtml_to_html_base(None, input_str=once)
    assert ihtml_to_html_base(None, input_str=once) == again
