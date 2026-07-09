"""Tests for :mod:`pytigon_lib.schhtml.pdfdc`."""

import io
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schhtml.basedc import BaseDc, BaseDcInfo
from pytigon_lib.schhtml.pdfdc import PdfDc, PdfDcInfo, PDFSurface


class TestPDFSurface:
    @pytest.fixture(autouse=True)
    def setup(self):
        with (
            patch("pytigon_lib.schhtml.pdfdc.FPDF", create=True) as mock_fpdf,
            patch("pytigon_lib.schhtml.pdfdc.IMAGE", create=True),
            patch("pytigon_lib.schhtml.pdfdc.get_main_paths", return_value={"STATIC_PATH": "/tmp"}),
        ):
            mock_fpdf.FPDF.return_value = MagicMock()
            mock_fpdf.fpdf.FPDF_FONT_DIR = "/tmp"
            yield

    def test_pdf_surface_stores_params(self):
        output_name = "test.pdf"
        output_stream = io.BytesIO()
        surf = PDFSurface(output_name, output_stream, 600, 800)
        assert surf.output_name == output_name
        assert surf.output_stream is output_stream
        assert surf.width == 600
        assert surf.height == 800

    def test_pdf_surface_orientation_landscape(self):
        surf = PDFSurface(None, None, 800, 600)
        assert surf.width > surf.height

    def test_pdf_surface_orientation_portrait(self):
        surf = PDFSurface(None, None, 600, 800)
        assert surf.height > surf.width

    def test_pdf_surface_fonts_map(self):
        surf = PDFSurface(None, None, 600, 800)
        assert surf.fonts_map["sans-serif"] == "sans-serif"
        assert surf.fonts_map["serif"] == "serif"
        assert surf.fonts_map["monospace"] == "monospace"
        assert surf.fonts_map["cursive"] == "sans-serif"
        assert surf.fonts_map["fantasy"] == "sans-serif"

    def test_pdf_surface_get_dc_returns_pdf(self):
        surf = PDFSurface(None, None, 600, 800)
        dc = surf.get_dc()
        assert dc is surf.pdf

    def test_pdf_surface_font_add_handles_error(self):
        surf = PDFSurface(None, None, 600, 800)
        assert surf.pdf is not None


class TestPdfDcConstructor:
    @patch("pytigon_lib.schhtml.pdfdc.FPDF", create=True)
    @patch("pytigon_lib.schhtml.pdfdc.IMAGE", create=True)
    @patch("pytigon_lib.schhtml.pdfdc.get_main_paths", return_value={"STATIC_PATH": "/tmp"})
    def setup_pdf_mocks(self, mock_paths, mock_image, mock_fpdf):
        mock_fpdf.FPDF.return_value = MagicMock()
        mock_fpdf.fpdf.FPDF_FONT_DIR = "/tmp"

    @pytest.fixture(autouse=True)
    def setup(self):
        with (
            patch("pytigon_lib.schhtml.pdfdc.FPDF", create=True) as mock_fpdf,
            patch("pytigon_lib.schhtml.pdfdc.IMAGE", create=True),
            patch("pytigon_lib.schhtml.pdfdc.get_main_paths", return_value={"STATIC_PATH": "/tmp"}),
        ):
            mock_fpdf.FPDF.return_value = MagicMock()
            mock_fpdf.fpdf.FPDF_FONT_DIR = "/tmp"
            yield

    def test_pdf_dc_inherits_from_base_dc(self):
        dc = PdfDc()
        assert isinstance(dc, BaseDc)

    def test_pdf_dc_default_dimensions(self):
        dc = PdfDc()
        assert dc.width == dc.default_width
        assert dc.height == dc.default_height

    def test_pdf_dc_custom_dimensions(self):
        dc = PdfDc(width=300, height=500)
        assert dc.width == 300
        assert dc.height == 500

    def test_pdf_dc_calc_only(self):
        dc = PdfDc(calc_only=True)
        assert dc.calc_only is True
        assert dc.width == -1
        assert dc.height == 1000000000

    def test_pdf_dc_calc_only_width_height_negative(self):
        dc = PdfDc(calc_only=True, width=-1, height=-1)
        assert dc.width == -1
        assert dc.height == 1000000000

    def test_pdf_dc_calc_only_width_height_positive(self):
        dc = PdfDc(calc_only=True, width=200, height=300)
        assert dc.width == 200
        assert dc.height == 300

    def test_pdf_dc_output_name(self):
        dc = PdfDc(output_name="out.pdf")
        assert dc.output_name == "out.pdf"

    def test_pdf_dc_output_stream(self):
        stream = io.BytesIO()
        dc = PdfDc(output_stream=stream)
        assert dc.output_stream is stream

    def test_pdf_dc_scale(self):
        dc = PdfDc(scale=1.5)
        assert dc.scale == 1.5

    def test_pdf_dc_init_drawing_state(self):
        dc = PdfDc()
        assert dc._color == (0, 0, 0, 255)
        assert dc._line_width == 0
        assert dc._fun_stack == []
        assert dc._fill is False
        assert dc._draw is False
        assert dc._preserve is False

    def test_pdf_dc_type_is_none(self):
        dc = PdfDc()
        assert dc.type is None

    def test_pdf_dc_dc_info_type(self):
        dc = PdfDc()
        assert isinstance(dc.dc_info, PdfDcInfo)

    def test_pdf_dc_recording(self):
        dc = PdfDc(record=True)
        assert dc.rec is True

    def test_pdf_dc_notify_callback_called_on_init(self):
        callback = MagicMock()
        dc = PdfDc(notify_callback=callback)
        callback.assert_any_call("start", {"dc": dc})
        assert callback.call_count >= 1

    def test_pdf_dc_external_dc(self):
        mock_dc = MagicMock()
        dc = PdfDc(dc=mock_dc)
        assert dc.surf is None
        assert dc.dc is mock_dc

    def test_pdf_dc_sets_last_style_tab_to_none(self):
        dc = PdfDc()
        assert dc.last_style_tab is None

    def test_pdf_dc_last_pen_and_brush_defaults(self):
        dc = PdfDc()
        assert dc._last_pen is None
        assert dc._last_brush is None
        assert dc._last_pen_color == (0, 0, 0, 255)
        assert dc._last_line_width == -1
        assert dc._last_brush_color == (255, 255, 255, 255)


class TestPdfDcAnnotate:
    @pytest.fixture(autouse=True)
    def setup(self):
        with (
            patch("pytigon_lib.schhtml.pdfdc.FPDF", create=True) as mock_fpdf,
            patch("pytigon_lib.schhtml.pdfdc.IMAGE", create=True),
            patch("pytigon_lib.schhtml.pdfdc.get_main_paths", return_value={"STATIC_PATH": "/tmp"}),
        ):
            mock_fpdf.FPDF.return_value = MagicMock()
            mock_fpdf.fpdf.FPDF_FONT_DIR = "/tmp"
            yield

    def test_annotate_returns_none_for_any_what(self):
        dc = PdfDc()
        result = dc.annotate("end_tag", {"element": MagicMock()})
        assert result is None

    def test_annotate_returns_none_for_start_tag(self):
        dc = PdfDc()
        result = dc.annotate("start_tag", {"element": MagicMock()})
        assert result is None

    def test_annotate_returns_none_for_empty_data(self):
        dc = PdfDc()
        result = dc.annotate("unknown", {})
        assert result is None


class TestPdfDcClose:
    @pytest.fixture(autouse=True)
    def setup(self):
        with (
            patch("pytigon_lib.schhtml.pdfdc.FPDF", create=True) as mock_fpdf,
            patch("pytigon_lib.schhtml.pdfdc.IMAGE", create=True),
            patch("pytigon_lib.schhtml.pdfdc.get_main_paths", return_value={"STATIC_PATH": "/tmp"}),
        ):
            mock_fpdf.FPDF.return_value = MagicMock()
            mock_fpdf.fpdf.FPDF_FONT_DIR = "/tmp"
            yield

    def test_close_calls_notify_callback_end(self):
        callback = MagicMock()
        dc = PdfDc(notify_callback=callback)
        callback.reset_mock()
        dc.close()
        callback.assert_called_once_with("end", {"dc": dc})

    def test_close_no_notify_callback_does_not_raise(self):
        dc = PdfDc()
        dc.close()

    def test_close_calc_only_does_not_save(self):
        dc = PdfDc(calc_only=True)
        dc.surf.save = MagicMock()
        dc.close()
        dc.surf.save.assert_not_called()

    def test_close_calls_surf_save(self):
        dc = PdfDc(output_name="test.pdf")
        dc.surf.save = MagicMock()
        dc.close()
        dc.surf.save.assert_called_once()

    def test_close_calls_surf_save_with_stream(self):
        stream = io.BytesIO()
        dc = PdfDc(output_stream=stream)
        dc.surf.save = MagicMock()
        dc.close()
        dc.surf.save.assert_called_once()


class TestPdfDcInfo:
    @pytest.fixture(autouse=True)
    def setup(self):
        with (
            patch("pytigon_lib.schhtml.pdfdc.FPDF", create=True) as mock_fpdf,
            patch("pytigon_lib.schhtml.pdfdc.IMAGE", create=True),
            patch("pytigon_lib.schhtml.pdfdc.get_main_paths", return_value={"STATIC_PATH": "/tmp"}),
        ):
            mock_fpdf.FPDF.return_value = MagicMock()
            mock_fpdf.fpdf.FPDF_FONT_DIR = "/tmp"
            yield

    def test_pdf_dc_info_constructor(self):
        dc = PdfDc()
        info = PdfDcInfo(dc)
        assert info.dc is dc

    def test_pdf_dc_info_inherits_from_base_dc_info(self):
        dc = PdfDc()
        info = PdfDcInfo(dc)
        assert isinstance(info, BaseDcInfo)

    def test_pdf_dc_info_get_line_dy_returns_height(self):
        dc = PdfDc()
        info = PdfDcInfo(dc)
        assert info.get_line_dy(15) == 15

    def test_pdf_dc_info_get_line_dy_zero(self):
        dc = PdfDc()
        info = PdfDcInfo(dc)
        assert info.get_line_dy(0) == 0

    def test_pdf_dc_info_get_img_size_returns_zero_on_error(self, monkeypatch):
        dc = PdfDc()
        info = PdfDcInfo(dc)
        from pytigon_lib.schhtml import pdfdc as pdfdc_module

        def raise_oserror(*args, **kwargs):
            raise OSError("decode error")

        monkeypatch.setattr(pdfdc_module.io, "BytesIO", lambda x: MagicMock(spec=io.BytesIO))
        monkeypatch.setattr(pdfdc_module.IMAGE, "open", raise_oserror)
        result = info.get_img_size(b"not-an-image")
        assert result == (0, 0)

    @patch("pytigon_lib.schhtml.pdfdc.IMAGE", create=True)
    def test_pdf_dc_info_get_img_size_returns_dimensions(self, mock_image):
        mock_img = MagicMock()
        mock_img.size = (100, 200)
        mock_image.open.return_value = mock_img
        dc = PdfDc()
        info = PdfDcInfo(dc)
        result = info.get_img_size(b"fake-png-data")
        assert result == (100, 200)
