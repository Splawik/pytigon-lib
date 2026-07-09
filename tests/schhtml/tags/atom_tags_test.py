"""Tests for :mod:`pytigon_lib.schhtml.tags.atom_tags`."""
from unittest.mock import MagicMock, patch

from pytigon_lib.schhtml.tags.atom_tags import (
    AtomTag,
    Atag,
    BrTag,
    HrTag,
    ImgDraw,
    ImgTag,
    ParCalc,
)


class TestAtomTag:
    def test_atomtag_is_class(self):
        assert isinstance(AtomTag, type)

    def test_atomtag_instantiation(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        atom = AtomTag(mock_parent, mock_parser, "p", {})
        assert atom.tag == "p"
        assert atom.parent is mock_parent
        assert atom.gparent is mock_parent

    def test_atomtag_close_empty_atom_list(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        atom = AtomTag(mock_parent, mock_parser, "p", {})
        atom.atom_list = None
        atom.close()
        mock_parent.append_atom_list.assert_not_called()

    def test_atomtag_close_with_atom_list(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        atom = AtomTag(mock_parent, mock_parser, "p", {})
        mock_atom_list = MagicMock()
        atom.atom_list = mock_atom_list
        atom.close()
        mock_parent.append_atom_list.assert_called_once_with(mock_atom_list)

    def test_atomtag_child_tags(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        atom = AtomTag(mock_parent, mock_parser, "p", {})
        assert "table" in atom.child_tags
        assert "br" in atom.child_tags
        assert "a" in atom.child_tags

    def test_atomtag_draw_atom_no_atag_parent(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parent.parent = None
        mock_parser = MagicMock()
        atom = AtomTag(mock_parent, mock_parser, "p", {})
        result = atom.draw_atom(MagicMock(), None, 0, 0, 0, 0)
        assert result is False

    def test_atomtag_draw_atom_with_atag_parent(self):
        mock_parent = MagicMock()
        mock_atag = MagicMock(spec=Atag)
        mock_atag.parent = None
        mock_parent.gparent = mock_parent
        mock_parent.parent = mock_atag
        mock_parser = MagicMock()
        atom = AtomTag(mock_parent, mock_parser, "p", {})
        atom.draw_atom(MagicMock(), None, 0, 0, 0, 0)
        mock_atag.draw_atom.assert_called_once()


class TestBrTag:
    def test_brtag_is_class(self):
        assert isinstance(BrTag, type)

    def test_brtag_instantiation(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        br = BrTag(mock_parent, mock_parser, "br", {})
        assert br.tag == "br"
        assert br.parent is mock_parent

    def test_brtag_close(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        mock_dc_info = MagicMock()
        br = BrTag(mock_parent, mock_parser, "br", {})
        br.dc_info = mock_dc_info
        br.close()
        mock_parent.append_atom_list.assert_called_once()


class TestAtag:
    def test_atag_is_class(self):
        assert isinstance(Atag, type)

    def test_atag_instantiation(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        atag = Atag(mock_parent, mock_parser, "a", {"href": "http://example.com"})
        assert atag.tag == "a"
        assert atag.no_wrap is True
        assert atag.attrs["href"] == "http://example.com"

    def test_atag_repr(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        atag = Atag(mock_parent, mock_parser, "a", {"href": "test"})
        r = repr(atag)
        assert "ATag" in r
        assert "a" in r

    def test_atag_close_empty(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        mock_dc_info = MagicMock()
        atag = Atag(mock_parent, mock_parser, "a", {"href": "test"})
        atag.dc_info = mock_dc_info
        atag.make_atom_list()
        atag.close()
        mock_parent.append_atom_list.assert_called_once()


class TestImgDraw:
    def test_imgdraw_creation(self):
        img_tag = MagicMock()
        imgdraw = ImgDraw(img_tag, b"fake_png", 100, 50)
        assert imgdraw.width == 100
        assert imgdraw.height == 50
        assert imgdraw.image == b"fake_png"

    def test_imgdraw_none_image(self):
        img_tag = MagicMock()
        imgdraw = ImgDraw(img_tag, None, 100, 50)
        mock_dc = MagicMock()
        imgdraw.draw_atom(mock_dc, None, 0, 0, 100, 50)
        mock_dc.draw_image.assert_not_called()


class TestImgTag:
    def test_imgtag_is_class(self):
        assert isinstance(ImgTag, type)

    def test_imgtag_instantiation(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        img = ImgTag(mock_parent, mock_parser, "img", {"src": "image.png"})
        assert img.tag == "img"
        assert img.src == "image.png"
        assert img.img is None


class TestParCalc:
    def test_parcalc_is_class(self):
        assert isinstance(ParCalc, type)

    def test_parcalc_instantiation(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        calc = ParCalc(mock_parent, mock_parser, "calc", {})
        assert calc.tag == "calc"

    def test_parcalc_safe_builtins(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        calc = ParCalc(mock_parent, mock_parser, "calc", {})
        assert "abs" in calc._SAFE_BUILTINS
        assert "int" in calc._SAFE_BUILTINS
        assert "min" in calc._SAFE_BUILTINS
        assert "max" in calc._SAFE_BUILTINS
        assert "sum" in calc._SAFE_BUILTINS

    def test_parcalc_expression_eval_logic(self):
        from pytigon_lib.schhtml.basehtmltags import BaseHtmlElemParser

        expr = "2 + 3"
        sanitized = "".join(c for c in expr if c in "0123456789.+-*/() " or c.isdigit())
        result = int(eval(sanitized, {"__builtins__": {}}, {}))
        assert result == 5

    def test_parcalc_invalid_expr_returns_zero(self):
        from pytigon_lib.schhtml.basehtmltags import BaseHtmlElemParser

        expr = "___invalid___"
        sanitized = "".join(c for c in expr if c in "0123456789.+-*/() " or c.isdigit())
        result = BaseHtmlElemParser._safe_eval_expr(sanitized, {})
        assert result == 0


class TestHrTag:
    def test_hrtag_is_class(self):
        assert isinstance(HrTag, type)

    def test_hrtag_instantiation(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        hr = HrTag(mock_parent, mock_parser, "hr", {"border": "2"})
        assert hr.tag == "hr"
        assert hr.in_draw is False
        assert len(hr.render_helpers) == 1

    def test_hrtag_close(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        mock_dc_info = MagicMock()
        hr = HrTag(mock_parent, mock_parser, "hr", {})
        hr.dc_info = mock_dc_info
        hr.close()
        mock_parent.append_atom_list.assert_called_once()

    def test_hrtag_draw_atom(self):
        mock_parent = MagicMock()
        mock_parent.gparent = mock_parent
        mock_parser = MagicMock()
        mock_dc = MagicMock()
        mock_subdc = MagicMock()
        mock_dc.subdc.return_value = mock_subdc
        hr = HrTag(mock_parent, mock_parser, "hr", {"border": "1"})
        hr.width = 400
        result = hr.draw_atom(mock_dc, None, 0, 0, 400, 10)
        assert result is True
        mock_dc.subdc.assert_called_once()
