from pytigon_lib.schhtml.atom import *

# Pytest tests
import pytest


def test_unescape():
    assert unescape("&gt; &lt; &amp; &quot;") == '> < & "'


def test_atom():
    atom = Atom("test", 10, 2, 5, 5)
    assert atom.get_width() == 10
    assert atom.get_height() == 10


def test_atom_line():
    line = AtomLine(100)
    atom = Atom("test", 50, 2, 5, 5)
    assert line.append(atom) is True
    assert line.dx == 50
    assert line.get_height() == 10


def test_atom_list():
    class DcInfo:
        def get_line_dy(self, dy):
            return dy

        def get_extents(self, text, style):
            return (len(text) * 10, 2, 5, 5)

    dc_info = DcInfo()
    atom_list = AtomList(dc_info)
    atom_list.append_text("Hello World", 0)
    assert len(atom_list.atom_list) == 2
    atom_list.gen_list_for_draw(100)
    assert atom_list.get_height() > 0


if __name__ == "__main__":
    pytest.main()
