from pytigon_lib.schhtml.css import *

# Pytest tests
import pytest


def test_comment_remover():
    css = "/* comment */ body { color: red; } // inline comment"
    assert comment_remover(css) == " body { color: red; } "


def test_csspos():
    pos = CssPos(["body"], {"color": "red"})
    assert pos.key() == "body"
    assert pos.attrs == {"color": "red"}


def test_css_parse_str():
    css = Css()
    css.parse_str("body { color: red; }")
    assert css.get_dict(None) == {}


def test_css_parse_indent_str():
    css = Css()
    css.parse_indent_str("body\n  color: red")
    assert css.get_dict(None) == {}


if __name__ == "__main__":
    pytest.main()
