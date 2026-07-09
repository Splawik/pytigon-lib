import pytest
from unittest.mock import MagicMock, patch

from pytigon_lib.schhtml.cairodc import CairoDc, CairoDcInfo, get_PdfCairoDc


class TestCairoDcConstructor:
    def test_default_constructor(self):
        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_surf = MagicMock()
            mock_ctx = MagicMock()
            mock_cairo.ImageSurface.return_value = mock_surf
            mock_cairo.Context.return_value = mock_ctx
            mock_cairo.FORMAT_RGB24 = 0
            mock_cairo.LINE_CAP_ROUND = 1

            dc = CairoDc()
            assert dc is not None

    def test_calc_only_constructor(self):
        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_surf = MagicMock()
            mock_ctx = MagicMock()
            mock_cairo.ImageSurface.return_value = mock_surf
            mock_cairo.Context.return_value = mock_ctx
            mock_cairo.FORMAT_RGB24 = 0

            dc = CairoDc(calc_only=True)
            assert dc.calc_only is True

    def test_constructor_with_ctx(self):
        mock_ctx = MagicMock()
        mock_ctx.set_line_cap = MagicMock()

        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_cairo.LINE_CAP_ROUND = 1
            dc = CairoDc(ctx=mock_ctx)
            assert dc.ctx is mock_ctx
            assert dc.surf is None

    def test_constructor_with_width_height(self):
        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_surf = MagicMock()
            mock_ctx = MagicMock()
            mock_cairo.ImageSurface.return_value = mock_surf
            mock_cairo.Context.return_value = mock_ctx
            mock_cairo.FORMAT_RGB24 = 0
            mock_cairo.LINE_CAP_ROUND = 1

            dc = CairoDc(width=500, height=600)
            assert dc.width == 500
            assert dc.height == 600

    def test_constructor_default_dimensions(self):
        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_surf = MagicMock()
            mock_ctx = MagicMock()
            mock_cairo.ImageSurface.return_value = mock_surf
            mock_cairo.Context.return_value = mock_ctx
            mock_cairo.FORMAT_RGB24 = 0
            mock_cairo.LINE_CAP_ROUND = 1

            dc = CairoDc(width=-1, height=-1)
            assert dc.width == dc.default_width
            assert dc.height == dc.default_height

    def test_constructor_with_scale(self):
        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_surf = MagicMock()
            mock_ctx = MagicMock()
            mock_cairo.ImageSurface.return_value = mock_surf
            mock_cairo.Context.return_value = mock_ctx
            mock_cairo.FORMAT_RGB24 = 0
            mock_cairo.LINE_CAP_ROUND = 1

            dc = CairoDc(scale=2.5)
            assert dc.scale == 2.5

    def test_constructor_with_notify_callback(self):
        cb = MagicMock()
        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_surf = MagicMock()
            mock_ctx = MagicMock()
            mock_cairo.ImageSurface.return_value = mock_surf
            mock_cairo.Context.return_value = mock_ctx
            mock_cairo.FORMAT_RGB24 = 0
            mock_cairo.LINE_CAP_ROUND = 1

            dc = CairoDc(notify_callback=cb)
            assert dc.notify_callback is cb

    def test_constructor_with_record(self):
        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_surf = MagicMock()
            mock_ctx = MagicMock()
            mock_cairo.ImageSurface.return_value = mock_surf
            mock_cairo.Context.return_value = mock_ctx
            mock_cairo.FORMAT_RGB24 = 0
            mock_cairo.LINE_CAP_ROUND = 1

            dc = CairoDc(record=True)
            assert dc.rec is True

    def test_constructor_sets_dc_info(self):
        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_surf = MagicMock()
            mock_ctx = MagicMock()
            mock_cairo.ImageSurface.return_value = mock_surf
            mock_cairo.Context.return_value = mock_ctx
            mock_cairo.FORMAT_RGB24 = 0
            mock_cairo.LINE_CAP_ROUND = 1

            dc = CairoDc()
            assert isinstance(dc.dc_info, CairoDcInfo)

    def test_pdf_output_name(self):
        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_surf = MagicMock()
            mock_ctx = MagicMock()
            mock_cairo.PDFSurface.return_value = mock_surf
            mock_cairo.Context.return_value = mock_ctx
            mock_cairo.FORMAT_RGB24 = 0
            mock_cairo.LINE_CAP_ROUND = 1

            dc = CairoDc(output_name="test.pdf", width=200, height=300)
            assert dc.type == "pdf"

    def test_svg_output_name(self):
        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_surf = MagicMock()
            mock_ctx = MagicMock()
            mock_cairo.SVGSurface.return_value = mock_surf
            mock_cairo.Context.return_value = mock_ctx
            mock_cairo.FORMAT_RGB24 = 0
            mock_cairo.LINE_CAP_ROUND = 1

            dc = CairoDc(output_name="test.svg", width=200, height=300)
            assert dc.type == "svg"

    def test_png_output_name(self):
        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_surf = MagicMock()
            mock_ctx = MagicMock()
            mock_cairo.ImageSurface.return_value = mock_surf
            mock_cairo.Context.return_value = mock_ctx
            mock_cairo.FORMAT_RGB24 = 0
            mock_cairo.LINE_CAP_ROUND = 1

            dc = CairoDc(output_name="test.png", width=200, height=300)
            assert dc.type == "png"


class TestCairoDcMethods:
    def test_get_size(self):
        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_surf = MagicMock()
            mock_ctx = MagicMock()
            mock_cairo.ImageSurface.return_value = mock_surf
            mock_cairo.Context.return_value = mock_ctx
            mock_cairo.FORMAT_RGB24 = 0
            mock_cairo.LINE_CAP_ROUND = 1

            dc = CairoDc(width=100, height=200)
            size = dc.get_size()
            assert size == [100, 200]

    def test_close_calc_only_noop(self):
        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_surf = MagicMock()
            mock_ctx = MagicMock()
            mock_cairo.ImageSurface.return_value = mock_surf
            mock_cairo.Context.return_value = mock_ctx
            mock_cairo.FORMAT_RGB24 = 0

            dc = CairoDc(calc_only=True)
            dc.close()
            mock_surf.finish.assert_not_called()

    def test_close_pdf_shows_page(self):
        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_surf = MagicMock()
            mock_ctx = MagicMock()
            mock_cairo.PDFSurface.return_value = mock_surf
            mock_cairo.Context.return_value = mock_ctx
            mock_cairo.FORMAT_RGB24 = 0
            mock_cairo.LINE_CAP_ROUND = 1

            dc = CairoDc(output_name="test.pdf", width=200, height=200)
            dc.close()
            mock_ctx.show_page.assert_called_once()
            mock_surf.finish.assert_called_once()

    def test_close_no_surf_noop(self):
        mock_ctx = MagicMock()
        mock_ctx.set_line_cap = MagicMock()
        mock_ctx.show_page = MagicMock()

        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_cairo.LINE_CAP_ROUND = 1
            dc = CairoDc(ctx=mock_ctx)
            dc.close()
            mock_ctx.show_page.assert_not_called()

    def test_set_color(self):
        mock_ctx = MagicMock()
        mock_ctx.set_line_cap = MagicMock()

        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_cairo.LINE_CAP_ROUND = 1
            dc = CairoDc(ctx=mock_ctx)
            dc.set_color(128, 64, 32)
            mock_ctx.set_source_rgb.assert_called_with(128 / 256.0, 64 / 256.0, 32 / 256.0)

    def test_set_line_width(self):
        mock_ctx = MagicMock()
        mock_ctx.set_line_cap = MagicMock()

        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_cairo.LINE_CAP_ROUND = 1
            dc = CairoDc(ctx=mock_ctx, scale=2.0)
            dc.set_line_width(5)
            mock_ctx.set_line_width.assert_called_with(10.0)

    def test_rgbfromhex(self):
        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_surf = MagicMock()
            mock_ctx = MagicMock()
            mock_cairo.ImageSurface.return_value = mock_surf
            mock_cairo.Context.return_value = mock_ctx
            mock_cairo.FORMAT_RGB24 = 0
            mock_cairo.LINE_CAP_ROUND = 1

            dc = CairoDc()
            r, g, b = dc.rgbfromhex("#ff8040")
            assert r == 255
            assert g == 128
            assert b == 64

    def test_rgbfromhex_short(self):
        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_surf = MagicMock()
            mock_ctx = MagicMock()
            mock_cairo.ImageSurface.return_value = mock_surf
            mock_cairo.Context.return_value = mock_ctx
            mock_cairo.FORMAT_RGB24 = 0
            mock_cairo.LINE_CAP_ROUND = 1

            dc = CairoDc()
            r, g, b = dc.rgbfromhex("#f00")
            assert r == 240
            assert g == 0
            assert b == 0

    def test_dx_property(self):
        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_surf = MagicMock()
            mock_ctx = MagicMock()
            mock_cairo.ImageSurface.return_value = mock_surf
            mock_cairo.Context.return_value = mock_ctx
            mock_cairo.FORMAT_RGB24 = 0
            mock_cairo.LINE_CAP_ROUND = 1

            dc = CairoDc(width=300)
            assert dc.dx == 300


class TestCairoDcInfo:
    def test_get_line_dy(self):
        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_surf = MagicMock()
            mock_ctx = MagicMock()
            mock_cairo.ImageSurface.return_value = mock_surf
            mock_cairo.Context.return_value = mock_ctx
            mock_cairo.FORMAT_RGB24 = 0
            mock_cairo.LINE_CAP_ROUND = 1

            dc = CairoDc()
            info = CairoDcInfo(dc)
            assert info.get_line_dy(2) == 24

    def test_get_extents(self):
        mock_ctx = MagicMock()
        mock_ctx.set_line_cap = MagicMock()
        mock_ctx.text_extents = MagicMock(return_value=(0, -6, 50, 12, 0, 0))
        mock_ctx.select_font_face = MagicMock()
        mock_ctx.set_font_size = MagicMock()
        mock_ctx.set_source_rgb = MagicMock()

        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_cairo.LINE_CAP_ROUND = 1
            dc = CairoDc(ctx=mock_ctx)
            dc.set_style = MagicMock(return_value=["#000", "sans-serif", "100", "0", "0", "0"])

            info = CairoDcInfo(dc)
            result = info.get_extents("test", 0)
            assert len(result) == 4

    def test_get_text_width(self):
        mock_ctx = MagicMock()
        mock_ctx.set_line_cap = MagicMock()
        mock_ctx.text_extents = MagicMock(return_value=(0, 0, 40, 12, 0, 0))
        mock_ctx.select_font_face = MagicMock()
        mock_ctx.set_font_size = MagicMock()
        mock_ctx.set_source_rgb = MagicMock()

        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_cairo.LINE_CAP_ROUND = 1
            dc = CairoDc(ctx=mock_ctx)
            dc.set_style = MagicMock(return_value=["#000", "sans-serif", "100", "0", "0", "0"])

            info = CairoDcInfo(dc)
            assert info.get_text_width("hello", 0) == 40


class TestGetPdfCairoDc:
    def test_get_pdf_cairo_dc(self):
        with patch("pytigon_lib.schhtml.cairodc.cairo") as mock_cairo:
            mock_surf = MagicMock()
            mock_ctx = MagicMock()
            mock_cairo.PDFSurface.return_value = mock_surf
            mock_cairo.Context.return_value = mock_ctx
            mock_cairo.FORMAT_RGB24 = 0
            mock_cairo.LINE_CAP_ROUND = 1

            dc = get_PdfCairoDc("output.pdf", 300, 400)
            assert dc is not None
            assert dc.width == 300
            assert dc.height == 400
            assert dc.calc_only is False
