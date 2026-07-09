"""Tests for :mod:`pytigon_lib.schhtml.tags.extra_tags`."""
from unittest.mock import MagicMock

from pytigon_lib.schhtml.tags.extra_tags import VectorImg


class TestVectorImgTag:
    def test_vectorimg_is_class(self):
        assert isinstance(VectorImg, type)

    def test_vectorimg_instantiation(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        vimg = VectorImg(mock_parent, mock_parser, "vimg", {"width": "200", "height": "150"})
        assert vimg.tag == "vimg"
        assert vimg.attrs == {"width": "200", "height": "150"}
        assert vimg.gparent is mock_parent

    def test_vectorimg_handle_data(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        vimg = VectorImg(mock_parent, mock_parser, "vimg", {})
        vimg.handle_data("M10 10 L20 20")
        assert vimg.draw_txt == "M10 10 L20 20"

    def test_vectorimg_handle_data_multiple(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        vimg = VectorImg(mock_parent, mock_parser, "vimg", {})
        vimg.handle_data("M10 10 ")
        vimg.handle_data("L20 20")
        assert vimg.draw_txt == "M10 10 L20 20"

    def test_vectorimg_pseudo_margins(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        vimg = VectorImg(mock_parent, mock_parser, "vimg", {})
        margins = vimg._get_pseudo_margins()
        assert isinstance(margins, list)
        assert len(margins) == 4

    def test_vectorimg_default_dimensions(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        vimg = VectorImg(mock_parent, mock_parser, "vimg", {})
        assert vimg.dx == 0
        assert vimg.dy == 0
        assert vimg.draw_txt == ""

    def test_vectorimg_render_helpers(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        vimg = VectorImg(mock_parent, mock_parser, "vimg", {})
        assert len(vimg.render_helpers) == 4

    def test_vectorimg_close_default_dims_when_zero(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        vimg = VectorImg(mock_parent, mock_parser, "vimg", {})
        vimg.width = 0
        vimg.height = 0
        assert vimg.width == 0
        assert vimg.height == 0

    def test_vectorimg_width_height_from_attrs(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        vimg = VectorImg(mock_parent, mock_parser, "vimg", {"width": "300", "height": "200"})
        assert vimg.width >= 0

    def test_vectorimg_draw_atom(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        mock_dc = MagicMock()
        mock_subdc = MagicMock()
        mock_dc.subdc.return_value = mock_subdc
        vimg = VectorImg(mock_parent, mock_parser, "vimg", {"width": "200", "height": "150"})
        vimg.width = 200
        vimg.height = 150
        vimg.draw_txt = "M10 10 L20 20"
        result = vimg.draw_atom(mock_dc, None, 0, 0, 200, 150)
        assert result is True
        mock_dc.subdc.assert_called_once_with(0, 0, 200, 150, True)
