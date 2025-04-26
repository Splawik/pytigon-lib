from pytigon_lib.schhtml.pdfdc import *
import PIL

# Pytest tests
import pytest


def test_pdf_surface_initialization():
    """Test PDFSurface initialization."""
    surface = PDFSurface("test.pdf", None, 100, 100)
    assert surface.width == 100
    assert surface.height == 100
    assert surface.pdf is not None


def test_pdf_dc_initialization():
    """Test PdfDc initialization."""
    dc = PdfDc(output_name="test.pdf", width=100, height=100)
    assert dc.width == 100
    assert dc.height == 100
    assert dc.dc is not None


def test_pdf_dc_draw_text():
    """Test drawing text in PdfDc."""
    dc = PdfDc(output_name="test.pdf", width=100, height=100)
    dc.draw_text(10, 10, "Hello, World!")
    assert len(dc._fun_stack) == 0  # No drawing functions should be added


def test_pdf_dc_draw_image():
    """Test drawing an image in PdfDc."""
    dc = PdfDc(output_name="test.pdf", width=100, height=100)
    with pytest.raises(PIL.UnidentifiedImageError):
        dc.draw_image(10, 10, 50, 50, 1, b"fake_png_data")


if __name__ == "__main__":
    pytest.main()
