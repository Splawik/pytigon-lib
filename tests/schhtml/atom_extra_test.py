import pytest
from unittest.mock import MagicMock, patch, PropertyMock

from pytigon_lib.schhtml.atom import (
    Atom,
    NullAtom,
    BrAtom,
    AtomLine,
    AtomList,
    unescape,
)


class TestUnescape:
    def test_unescape_gt(self):
        assert unescape("&gt;") == ">"

    def test_unescape_lt(self):
        assert unescape("&lt;") == "<"

    def test_unescape_amp(self):
        assert unescape("&amp;") == "&"

    def test_unescape_quot(self):
        assert unescape("&quot;") == '"'

    def test_unescape_mixed(self):
        assert unescape("&lt;a&amp;b&gt;") == "<a&b>"


class TestAtomExtra:
    def test_atom_is_txt_false_by_default(self):
        a = Atom("data", 10, 2, 5, 5)
        assert a.is_txt is False

    def test_atom_is_txt_true(self):
        a = Atom("data", 10, 2, 5, 5, is_txt=True)
        assert a.is_txt is True

    def test_atom_default_style(self):
        a = Atom("data", 10, 2, 5, 5)
        assert a.style == -1

    def test_atom_custom_style(self):
        a = Atom("data", 10, 2, 5, 5, style=3)
        assert a.style == 3

    def test_atom_get_width(self):
        a = Atom("x", 42, 5, 7, 3)
        assert a.get_width() == 42

    def test_atom_get_height(self):
        a = Atom("x", 10, 2, 8, 4)
        assert a.get_height() == 12

    def test_atom_set_and_get_parent(self):
        parent = MagicMock()
        a = Atom("x", 10, 2, 5, 5)
        a.set_parent(parent)
        assert a.get_parent() is parent

    def test_atom_parent_none_by_default(self):
        a = Atom("x", 10, 2, 5, 5)
        assert a.get_parent() is None


class TestNullAtom:
    def test_null_atom_has_zero_dimensions(self):
        na = NullAtom()
        assert na.get_width() == 0
        assert na.get_height() == 0

    def test_null_atom_empty_data(self):
        na = NullAtom()
        assert na.data == ""

    def test_null_atom_draw_atom(self):
        na = NullAtom()
        assert na.draw_atom(None, 0, 0, 0) is True


class TestBrAtom:
    def test_br_atom_default_cr_count(self):
        ba = BrAtom()
        assert ba.cr_count == 1

    def test_br_atom_custom_cr_count(self):
        ba = BrAtom(cr_count=3)
        assert ba.cr_count == 3

    def test_br_atom_is_null_atom_subclass(self):
        ba = BrAtom()
        assert isinstance(ba, NullAtom)
        assert isinstance(ba, Atom)


class TestAtomLine:
    def test_atom_line_append_fits(self):
        line = AtomLine(100)
        atom = Atom("test", 40, 5, 6, 6)
        assert line.append(atom) is True
        assert atom in line.objs

    def test_atom_line_append_exceeds_maxwidth(self):
        line = AtomLine(100)
        atom = Atom("test", 120, 5, 6, 6)
        assert line.append(atom) is False

    def test_atom_line_force_append(self):
        line = AtomLine(100)
        atom = Atom("test", 120, 5, 6, 6)
        assert line.append(atom, force_append=True) is True

    def test_atom_line_tracks_dx(self):
        line = AtomLine(200)
        line.append(Atom("a", 30, 5, 6, 6))
        line.append(Atom("b", 50, 5, 6, 6))
        assert line.dx == 80

    def test_atom_line_get_height(self):
        line = AtomLine(200)
        line.append(Atom("a", 30, 5, 10, 5))
        assert line.get_height() == 15

    def test_atom_line_not_justify(self):
        line = AtomLine(200)
        line.not_justify = True
        line.append(Atom("a", 30, 5, 6, 6))
        line.justify()
        assert len(line.objs) == 1

    def test_atom_line_justify_adds_spacers(self):
        line = AtomLine(200)
        line.append(Atom("a", 30, 5, 6, 6))
        line.append(Atom("b", 40, 5, 6, 6))
        line.justify()
        assert len(line.objs) == 3

    def test_atom_line_justify_from_second(self):
        line = AtomLine(200)
        line.maxwidth = 150
        line.append(Atom("a", 30, 5, 6, 6))
        line.append(Atom("b", 40, 5, 6, 6))
        line.justify(from_second=True)
        assert len(line.objs) == 2

    def test_atom_line_pop_if_one_char(self):
        line = AtomLine(200)
        line.append(Atom("a", 30, 5, 6, 6))
        line.append(Atom("b", 30, 5, 6, 6))
        line.append(Atom("x", 15, 5, 6, 6, is_txt=True))
        popped = line.pop_if_one_char()
        assert popped is not None
        assert popped.data == "x"

    def test_atom_line_pop_if_one_char_too_few(self):
        line = AtomLine(200)
        line.append(Atom("a", 30, 5, 6, 6, is_txt=True))
        assert line.pop_if_one_char() is None


class TestAtomList:
    def _make_dc_info(self):
        dc_info = MagicMock()
        dc_info.get_line_dy.return_value = 12
        dc_info.get_extents.return_value = (50, 5, 6, 6)
        return dc_info

    def test_atom_list_append_text(self):
        dc_info = self._make_dc_info()
        al = AtomList(dc_info)
        al.append_text("Hello World", 0)
        assert len(al.atom_list) == 2

    def test_atom_list_append_atom(self):
        dc_info = self._make_dc_info()
        al = AtomList(dc_info)
        atom = Atom("x", 10, 2, 5, 5)
        al.append_atom(atom)
        assert len(al.atom_list) == 1

    def test_atom_list_set_first_line_offset(self):
        dc_info = self._make_dc_info()
        al = AtomList(dc_info)
        al.set_first_line_offset(20)
        assert al.first_line_offset == 20

    def test_atom_list_set_justify(self):
        dc_info = self._make_dc_info()
        al = AtomList(dc_info)
        al.set_justify()
        assert al.justify is True

    def test_atom_list_set_leave_single_char(self):
        dc_info = self._make_dc_info()
        al = AtomList(dc_info)
        al.set_leave_single_char(False)
        assert al.leave_single_char is False

    def test_atom_list_set_line_dy(self):
        dc_info = self._make_dc_info()
        dc_info.get_line_dy.return_value = 36
        al = AtomList(dc_info)
        al.set_line_dy(3)
        assert al.line_dy == 36

    def test_atom_list_gen_list_for_draw(self):
        dc_info = self._make_dc_info()
        al = AtomList(dc_info)
        al.append_text("Hello World", 0)
        al.gen_list_for_draw(200)
        assert al.list_for_draw is not None
        assert len(al.list_for_draw) > 0

    def test_atom_list_get_height(self):
        dc_info = self._make_dc_info()
        al = AtomList(dc_info)
        al.append_text("test", 0)
        al.gen_list_for_draw(200)
        assert al.get_height() > 0

    def test_atom_list_get_height_empty(self):
        dc_info = self._make_dc_info()
        al = AtomList(dc_info)
        assert al.get_height() == -1

    def test_atom_list_pre_mode(self):
        dc_info = self._make_dc_info()
        al = AtomList(dc_info, pre=True)
        al.append_text("line1\nline2", 0)
        assert len(al.atom_list) >= 2

    def test_atom_list_to_txt(self):
        dc_info = self._make_dc_info()
        al = AtomList(dc_info)
        al.append_text("Hello", 0)
        result = al.to_txt()
        assert result == "Hello"

    def test_atom_list_append_empty_text(self):
        dc_info = self._make_dc_info()
        al = AtomList(dc_info)
        al.append_text("", 0)
        assert len(al.atom_list) == 0

    def test_atom_list_br_atom_in_list(self):
        dc_info = self._make_dc_info()
        dc_info.get_extents.return_value = (50, 5, 6, 6)
        al = AtomList(dc_info, pre=True)
        al.append_text("Hello\nWorld", 0)
        al.gen_list_for_draw(500)
        assert len(al.list_for_draw) == 2

    def test_atom_list_draw_atom_list_basic(self):
        dc_info = self._make_dc_info()
        al = AtomList(dc_info)
        al.append_text("test", 0)
        al.gen_list_for_draw(200)

        subdc = MagicMock()
        dc = MagicMock()
        dc.get_size.return_value = [200, 100]
        dc.subdc.return_value = subdc

        al.draw_atom_list(dc)
        assert dc.subdc.called
        assert subdc.draw_atom_line.called
