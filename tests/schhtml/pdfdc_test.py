"""Tests for :mod:`pytigon_lib.schhtml.pdfdc`."""

import io
import os
import pathlib
import tempfile

import pytest

from pytigon_lib.schhtml.pdfdc import (
    PdfDc,
    PdfDcInfo,
    PDFSurface,
)

TEST_PATH = pathlib.Path(__file__).parent.resolve()
STATIC_PATH = TEST_PATH / "static"


def _valid_png_bytes():
    """Return bytes of a small valid PNG file from the test assets."""
    png_path = STATIC_PATH / "pytigon.png"
    if png_path.exists():
        return png_path.read_bytes()
    # Fallback: minimal 1x1 white PNG
    return (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f"
        b"\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
    )


# ============================================================================
# PDFSurface
# ============================================================================


class TestPDFSurface:
    """Tests for :class:`PDFSurface`."""

    def test_initialization_creates_pdf(self):
        surface = PDFSurface("test.pdf", None, 100, 200)
        assert surface.width == 100
        assert surface.height == 200
        assert surface.pdf is not None
        assert surface.output_name == "test.pdf"
        assert surface.output_stream is None

    def test_initialization_with_output_stream(self):
        stream = io.BytesIO()
        surface = PDFSurface(None, stream, 300, 400)
        assert surface.output_name is None
        assert surface.output_stream is stream

    def test_landscape_orientation(self):
        """Width > height should select landscape orientation."""
        surface = PDFSurface("test.pdf", None, 800, 600)
        assert surface.pdf is not None

    def test_portrait_orientation(self):
        """Height >= width should select portrait orientation."""
        surface = PDFSurface("test.pdf", None, 600, 800)
        assert surface.pdf is not None

    def test_get_dc_returns_pdf(self):
        surface = PDFSurface("test.pdf", None, 100, 100)
        dc = surface.get_dc()
        assert dc is surface.pdf

    def test_save_to_file(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_name = tmp.name
        try:
            surface = PDFSurface(tmp_name, None, 100, 100)
            surface.pdf.add_page()
            surface.save()
            assert os.path.exists(tmp_name)
            assert os.path.getsize(tmp_name) > 0
        finally:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)

    def test_save_to_stream(self):
        stream = io.BytesIO()
        surface = PDFSurface(None, stream, 100, 100)
        surface.pdf.add_page()
        surface.save()
        assert stream.tell() > 0

    def test_font_map_contains_expected_keys(self):
        surface = PDFSurface("test.pdf", None, 100, 100)
        assert "sans-serif" in surface.fonts_map
        assert "serif" in surface.fonts_map
        assert "monospace" in surface.fonts_map


# ============================================================================
# PdfDc
# ============================================================================


class TestPdfDc:
    """Tests for :class:`PdfDc`."""

    # -- initialization ------------------------------------------------------

    def test_initialization_basic(self):
        dc = PdfDc(output_name="test.pdf", width=100, height=200)
        assert dc.width == 100
        assert dc.height == 200
        assert dc.dc is not None

    def test_initialization_with_custom_dimensions(self):
        dc = PdfDc(output_name="test.pdf", width=800, height=600)
        assert dc.width == 800
        assert dc.height == 600

    def test_initialization_calc_only(self):
        """calc_only=True creates a lightweight DC for measurement."""
        dc = PdfDc(calc_only=True, width=100, height=100)
        assert dc.calc_only is True
        assert dc.dc is not None

    def test_initialization_default_dimensions(self):
        """width=None / height=None should use defaults."""
        dc = PdfDc(output_name="test.pdf")
        assert dc.dc is not None

    def test_initialization_external_dc(self):
        """An externally-provided DC is used instead of creating a new surface."""
        surface = PDFSurface("test.pdf", None, 100, 100)
        external_dc = surface.get_dc()
        dc = PdfDc(dc=external_dc, width=100, height=100)
        assert dc.dc is external_dc
        assert dc.surf is None

    # -- draw_text -----------------------------------------------------------

    def test_draw_text(self):
        dc = PdfDc(output_name="test.pdf", width=100, height=100)
        dc.draw_text(10, 10, "Hello, World!")
        assert dc.dc is not None

    def test_draw_text_empty(self):
        dc = PdfDc(output_name="test.pdf", width=100, height=100)
        dc.draw_text(10, 10, "")
        assert dc.dc is not None

    # -- draw_image ----------------------------------------------------------

    def test_draw_image_invalid_png_raises_runtimeerror(self):
        """Invalid PNG data is wrapped in a RuntimeError."""
        dc = PdfDc(output_name="test.pdf", width=100, height=100)
        with pytest.raises(RuntimeError, match="Failed to decode image"):
            dc.draw_image(10, 10, 50, 50, 1, b"fake_png_data")

    def test_draw_image_no_pil_raises_importerror(self, monkeypatch):
        """When PIL is unavailable, draw_image raises ImportError."""
        import pytigon_lib.schhtml.pdfdc as pdfdc_mod

        dc = PdfDc(output_name="test.pdf", width=100, height=100)
        monkeypatch.setattr(pdfdc_mod, "IMAGE", None)
        with pytest.raises(ImportError, match="PIL is required"):
            dc.draw_image(10, 10, 50, 50, 0, _valid_png_bytes())

    # -- close ---------------------------------------------------------------

    def test_close_saves_pdf(self):
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp_name = tmp.name
        try:
            dc = PdfDc(output_name=tmp_name, width=100, height=100)
            dc.draw_text(10, 10, "test")
            dc.close()
            assert os.path.exists(tmp_name)
            assert os.path.getsize(tmp_name) > 0
        finally:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)

    def test_close_calc_only_does_not_save(self):
        """calc_only DCs do not write a file on close."""
        dc = PdfDc(calc_only=True, width=100, height=100)
        dc.close()  # should not raise

    # -- color and line width ------------------------------------------------

    def test_set_color(self):
        dc = PdfDc(output_name="test.pdf", width=100, height=100)
        dc.set_color(255, 0, 0, 128)
        assert dc._color == (255, 0, 0, 128)

    def test_set_line_width(self):
        dc = PdfDc(output_name="test.pdf", width=100, height=100)
        dc.set_line_width(3)
        assert dc._line_width == 3

    # -- drawing operations (stack based) ------------------------------------

    def test_add_line_appends_to_stack(self):
        dc = PdfDc(output_name="test.pdf", width=100, height=100)
        initial_len = len(dc._fun_stack)
        dc.add_line(0, 0, 50, 50)
        assert len(dc._fun_stack) == initial_len + 1

    def test_draw_clears_stack(self):
        dc = PdfDc(output_name="test.pdf", width=100, height=100)
        dc.add_line(0, 0, 50, 50)
        dc.draw()
        assert len(dc._fun_stack) == 0

    def test_draw_preserve_keeps_stack(self):
        dc = PdfDc(output_name="test.pdf", width=100, height=100)
        dc.add_line(0, 0, 50, 50)
        dc.draw(preserve=True)
        assert len(dc._fun_stack) == 1

    # -- pages ---------------------------------------------------------------

    def test_start_page(self):
        dc = PdfDc(output_name="test.pdf", width=100, height=100)
        initial_page = dc.dc.page
        dc.start_page()
        assert dc.dc.page == initial_page + 1


# ============================================================================
# PdfDcInfo
# ============================================================================


class TestPdfDcInfo:
    """Tests for :class:`PdfDcInfo`."""

    def test_initialization(self):
        dc = PdfDc(output_name="test.pdf", width=100, height=100)
        info = PdfDcInfo(dc)
        assert info.dc is dc
