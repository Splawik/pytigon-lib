"""Tests for :mod:`pytigon_lib.schhtml.wxdc`."""

import io
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schhtml.basedc import BaseDc


class TestDcDcInit:
    @pytest.fixture(autouse=True)
    def setup_wx_mock(self):
        with patch("wx.Bitmap", create=True) as mock_bitmap, \
             patch("wx.MemoryDC", create=True) as mock_memdc, \
             patch("wx.EmptyBitmap", create=True) as mock_empty, \
             patch("wx.Brush", create=True) as mock_brush, \
             patch("wx.Pen", create=True) as mock_pen, \
             patch("wx.Colour", create=True) as mock_color, \
             patch("wx.SystemSettings.GetFont", create=True) as mock_font, \
             patch("wx.Image", create=True) as mock_image, \
             patch("wx.ImageFromStream", create=True) as mock_fromstream:
            mock_bitmap.return_value = MagicMock()
            mock_memdc.return_value = MagicMock()
            mock_empty.return_value = MagicMock()
            mock_brush.return_value = MagicMock()
            mock_pen.return_value = MagicMock()
            mock_color.return_value = MagicMock()
            mock_font_obj = MagicMock()
            mock_font_obj.GetFamily.return_value = 0
            mock_font_obj.GetFaceName.return_value = ""
            mock_font_obj.GetWeight.return_value = 0
            mock_font_obj.GetStyle.return_value = 0
            mock_font_obj.GetPointSize.return_value = 10
            mock_font.return_value = mock_font_obj
            mock_image.return_value = MagicMock()
            mock_fromstream.return_value = MagicMock()

            from pytigon_lib.schhtml.wxdc import DcDc, DcDcinfo

            self.DcDc = DcDc
            self.DcDcinfo = DcDcinfo
            yield

    def test_initialization_basic(self):
        dc = self.DcDc()
        assert isinstance(dc, BaseDc)
        assert dc.calc_only is False
        assert dc.dc_info is not None

    def test_initialization_calc_only(self):
        dc = self.DcDc(calc_only=True)
        assert dc.calc_only is True
        assert dc.width == -1
        assert dc.height == 1000000000

    def test_initialization_default_dimensions(self):
        dc = self.DcDc()
        assert dc.width == dc.default_width
        assert dc.height == dc.default_height

    def test_initialization_custom_dimensions(self):
        dc = self.DcDc(width=500, height=300)
        assert dc.width == 500
        assert dc.height == 300

    def test_initialization_with_output_name_png(self):
        dc = self.DcDc(output_name="test.png")
        assert dc.type == "png"

    def test_initialization_with_output_name_jpg(self):
        dc = self.DcDc(output_name="test.jpg")
        assert dc.type == "jpg"

    def test_initialization_with_output_name_jpeg(self):
        dc = self.DcDc(output_name="test.jpeg")
        assert dc.type == "jpg"

    def test_initialization_dc_info_type(self):
        dc = self.DcDc()
        assert isinstance(dc.dc_info, self.DcDcinfo)

    def test_initialization_color_defaults(self):
        dc = self.DcDc()
        assert dc._color == (0, 0, 0, 255)
        assert dc._line_width == 0
        assert dc._draw is False
        assert dc._fill is False

    def test_initialization_fun_stack_empty(self):
        dc = self.DcDc()
        assert dc._fun_stack == []

    def test_initialization_scale(self):
        dc = self.DcDc(scale=2.0)
        assert dc.scale == 2.0

    def test_initialization_with_output_stream(self):
        stream = io.BytesIO()
        dc = self.DcDc(output_stream=stream)
        assert dc.output_stream is stream


class TestDcDcClose:
    @pytest.fixture(autouse=True)
    def setup_wx_mock(self):
        with patch("wx.Bitmap", create=True), \
             patch("wx.MemoryDC", create=True), \
             patch("wx.EmptyBitmap", create=True), \
             patch("wx.Brush", create=True), \
             patch("wx.Pen", create=True), \
             patch("wx.Colour", create=True), \
             patch("wx.SystemSettings.GetFont", create=True), \
             patch("wx.Image", create=True), \
             patch("wx.ImageFromStream", create=True):
            from pytigon_lib.schhtml.wxdc import DcDc
            self.DcDc = DcDc
            yield

    def test_close_calc_only_does_nothing(self):
        dc = self.DcDc(calc_only=True)
        dc.close()


class TestDcDcMethods:
    @pytest.fixture(autouse=True)
    def setup_wx_mock(self):
        with patch("wx.Bitmap", create=True), \
             patch("wx.MemoryDC", create=True), \
             patch("wx.EmptyBitmap", create=True), \
             patch("wx.Brush", create=True), \
             patch("wx.Pen", create=True), \
             patch("wx.Colour", create=True), \
             patch("wx.SystemSettings.GetFont", create=True), \
             patch("wx.Image", create=True), \
             patch("wx.ImageFromStream", create=True):
            from pytigon_lib.schhtml.wxdc import DcDc
            self.DcDc = DcDc
            yield

    def test_set_color(self):
        dc = self.DcDc()
        dc.set_color(128, 64, 32, 200)
        assert dc._color == (128, 64, 32, 200)

    def test_set_line_width(self):
        dc = self.DcDc()
        dc.set_line_width(5)
        assert dc._line_width == 5

    def test_add_line(self):
        dc = self.DcDc()
        dc.add_line(0, 0, 50, 50)
        assert len(dc._fun_stack) == 1

    def test_add_rectangle(self):
        dc = self.DcDc()
        dc.add_rectangle(10, 10, 100, 50)
        assert len(dc._fun_stack) == 1

    def test_add_ellipse(self):
        dc = self.DcDc()
        dc.add_ellipse(10, 10, 100, 50)
        assert len(dc._fun_stack) == 1

    def test_set_scale_resets_pen(self):
        dc = self.DcDc(scale=1.0)
        dc._last_pen = MagicMock()
        dc._last_line_width = 5
        dc.set_scale(2.0)
        assert dc._last_pen is None
        assert dc._last_line_width == -1


class TestDcDcInfo:
    @pytest.fixture(autouse=True)
    def setup_wx_mock(self):
        with patch("wx.Bitmap", create=True), \
             patch("wx.MemoryDC", create=True), \
             patch("wx.EmptyBitmap", create=True), \
             patch("wx.Brush", create=True), \
             patch("wx.Pen", create=True), \
             patch("wx.Colour", create=True), \
             patch("wx.SystemSettings.GetFont", create=True), \
             patch("wx.Image", create=True), \
             patch("wx.ImageFromStream", create=True):
            from pytigon_lib.schhtml.wxdc import DcDc, DcDcinfo
            self.DcDc = DcDc
            self.DcDcinfo = DcDcinfo
            yield

    def test_initialization(self):
        dc = self.DcDc()
        info = self.DcDcinfo(dc)
        assert info.dc is dc

    def test_get_line_dy(self):
        dc = self.DcDc()
        info = self.DcDcinfo(dc)
        assert info.get_line_dy(12) == 36
