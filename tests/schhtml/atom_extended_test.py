"""Tests for :mod:`pytigon_lib.schhtml.atom`."""
import pytest

from pytigon_lib.schhtml.atom import (
    Atom,
    BrAtom,
    NullAtom,
    unescape,
    DECODE_SYM,
)


class TestUnescape:
    def test_gt(self):
        assert unescape("a &gt; b") == "a > b"

    def test_lt(self):
        assert unescape("a &lt; b") == "a < b"

    def test_amp(self):
        assert unescape("a &amp; b") == "a & b"

    def test_quot(self):
        assert unescape('&quot;hello&quot;') == '"hello"'

    def test_no_entities(self):
        assert unescape("plain text") == "plain text"

    def test_multiple_entities(self):
        assert unescape("&lt;a&amp;b&gt;") == "<a&b>"


class TestDecodeSym:
    def test_is_tuple_of_pairs(self):
        assert isinstance(DECODE_SYM, tuple)
        assert all(isinstance(p, tuple) and len(p) == 2 for p in DECODE_SYM)


class TestAtom:
    def test_init_defaults(self):
        a = Atom("data", 10, 12, 5, 3)
        assert a.data == "data"
        assert a.dx == 10
        assert a.dx_space == 12
        assert a.dy_up == 5
        assert a.dy_down == 3

    def test_get_width(self):
        a = Atom("data", 10, 12, 5, 3)
        assert a.get_width() == 10

    def test_get_height(self):
        a = Atom("data", 10, 12, 5, 3)
        assert a.get_height() == 8

    def test_set_parent(self):
        a = Atom("data", 10, 12, 5, 3)
        parent = Atom("parent", 20, 22, 7, 5)
        a.set_parent(parent)
        assert a.get_parent() is parent

    def test_get_parent_none(self):
        a = Atom("data", 10, 12, 5, 3)
        assert a.get_parent() is None

    def test_style_default(self):
        a = Atom("data", 10, 12, 5, 3)
        assert a.style == -1

    def test_is_txt_default(self):
        a = Atom("data", 10, 12, 5, 3)
        assert a.is_txt is False

    def test_is_txt_true(self):
        a = Atom("data", 10, 12, 5, 3, is_txt=True)
        assert a.is_txt is True

    def test_parent_default(self):
        a = Atom("data", 10, 12, 5, 3)
        assert a.parent is None


class TestNullAtom:
    def test_init(self):
        na = NullAtom()
        assert na.data == ""
        assert na.dx == 0
        assert na.dx_space == 0
        assert na.dy_up == 0
        assert na.dy_down == 0

    def test_draw_atom(self):
        na = NullAtom()
        result = na.draw_atom(None, None, 0, 0)
        assert result is True


class TestBrAtom:
    def test_init(self):
        br = BrAtom()
        assert br.cr_count == 1

    def test_init_with_count(self):
        br = BrAtom(3)
        assert br.cr_count == 3

    def test_inherits_null_atom(self):
        br = BrAtom()
        assert isinstance(br, NullAtom)

    def test_draw_atom(self):
        br = BrAtom()
        result = br.draw_atom(None, None, 0, 0)
        assert result is True
