from pytigon_lib.schhtml.parser import *

# Pytest tests
import pytest


def test_parser_init():
    parser = Parser()
    assert parser._tree is None
    assert parser._cur_elem is None


def test_elem_str():
    elem = etree.Element("div")
    elem_obj = Elem(elem)
    assert "<div></div>" in str(elem_obj)


def test_elem_len():
    elem = etree.Element("div")
    elem.text = "Hello"
    elem_obj = Elem(elem)
    assert len(elem_obj) == len("<div>Hello</div>\n")


def test_elem_bool():
    elem = etree.Element("div")
    elem_obj = Elem(elem)
    assert bool(elem_obj) is True
    elem_obj = Elem(None)
    assert bool(elem_obj) is False


def test_super_strip():
    elem = Elem(etree.Element("div"))
    assert elem.super_strip("  \n  Hello  \n  ") == "Hello"


def test_tostream():
    elem = etree.Element("div")
    elem.text = "Hello"
    elem_obj = Elem(elem)
    output = elem_obj.tostream()
    assert output.getvalue() == "div...Hello\n"


if __name__ == "__main__":
    pytest.main()
