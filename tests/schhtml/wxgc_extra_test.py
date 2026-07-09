"""Extra tests for :mod:`pytigon_lib.schhtml.wxgc`."""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_wx():
    with patch("pytigon_lib.schhtml.wxgc.wx") as mock:
        mock.EmptyBitmap.return_value = MagicMock()
        mock.MemoryDC.return_value = MagicMock()
        mock.Colour.return_value = MagicMock()
        mock.Pen.return_value = MagicMock()
        mock.Brush.return_value = MagicMock()

        mock_font = MagicMock()
        mock_font.SetStyle = MagicMock()
        mock_font.SetWeight = MagicMock()
        mock_font.SetFamily = MagicMock()
        mock_font.SetPointSize = MagicMock()
        mock.SystemSettings.GetFont.return_value = mock_font

        mock_path = MagicMock()
        mock_gc = MagicMock()
        mock_gc.CreatePath.return_value = mock_path
        mock.GraphicsContext.Create.return_value = mock_gc
        yield mock


class TestGraphicsContextDcExtra:
    def test_init_calc_only_default(self, mock_wx):
        from pytigon_lib.schhtml.wxgc import GraphicsContextDc

        dc = GraphicsContextDc(calc_only=True)
        assert dc.calc_only is True

    def test_init_with_width_height(self, mock_wx):
        from pytigon_lib.schhtml.wxgc import GraphicsContextDc

        dc = GraphicsContextDc(calc_only=True, width=100, height=200)
        assert dc.width == 100
        assert dc.height == 200

    def test_init_sets_colour_default(self, mock_wx):
        from pytigon_lib.schhtml.wxgc import GraphicsContextDc

        GraphicsContextDc(calc_only=True)
        mock_wx.Colour.assert_called_with(0, 0, 0)

    def test_init_sets_line_width(self, mock_wx):
        from pytigon_lib.schhtml.wxgc import GraphicsContextDc

        dc = GraphicsContextDc(calc_only=True)
        assert dc.line_width == 1

    def test_init_sets_move_coords(self, mock_wx):
        from pytigon_lib.schhtml.wxgc import GraphicsContextDc

        dc = GraphicsContextDc(calc_only=True)
        assert dc._move_x == 0
        assert dc._move_y == 0

    def test_init_last_style_tab_is_none(self, mock_wx):
        from pytigon_lib.schhtml.wxgc import GraphicsContextDc

        dc = GraphicsContextDc(calc_only=True)
        assert dc.last_style_tab is None

    def test_dc_info_present(self, mock_wx):
        from pytigon_lib.schhtml.wxgc import GraphicsContextDc

        dc = GraphicsContextDc(calc_only=True)
        assert dc.dc_info is not None

    def test_type_is_none_by_default(self, mock_wx):
        from pytigon_lib.schhtml.wxgc import GraphicsContextDc

        dc = GraphicsContextDc(calc_only=True)
        assert dc.type is None

    def test_path_is_none_by_default(self, mock_wx):
        from pytigon_lib.schhtml.wxgc import GraphicsContextDc

        dc = GraphicsContextDc(calc_only=True)
        assert dc.path is None

    def test_new_path_creates_path(self, mock_wx):
        from pytigon_lib.schhtml.wxgc import GraphicsContextDc

        dc = GraphicsContextDc(calc_only=True)
        dc.new_path()
        assert dc.path is not None


class TestGraphicsContextDcinfoExtra:
    def test_init(self, mock_wx):
        from pytigon_lib.schhtml.wxgc import GraphicsContextDc, GraphicsContextDcinfo

        dc = GraphicsContextDc(calc_only=True)
        info = GraphicsContextDcinfo(dc)
        assert info is not None

    def test_get_line_dy(self, mock_wx):
        from pytigon_lib.schhtml.wxgc import GraphicsContextDc, GraphicsContextDcinfo

        dc = GraphicsContextDc(calc_only=True)
        info = GraphicsContextDcinfo(dc)
        assert info.get_line_dy(10) == 30
        assert info.get_line_dy(5) == 15
        assert info.get_line_dy(0) == 0
        assert info.get_line_dy(1) == 3

    def test_get_img_size_returns_tuple(self, mock_wx):
        from pytigon_lib.schhtml.wxgc import GraphicsContextDc, GraphicsContextDcinfo

        dc = GraphicsContextDc(calc_only=True)
        mock_wx.ImageFromStream.side_effect = Exception("no image")
        info = GraphicsContextDcinfo(dc)
        w, h = info.get_img_size(b"not an image")
        assert w == 0
        assert h == 0
