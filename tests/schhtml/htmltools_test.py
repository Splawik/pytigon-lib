from pytigon_lib.schhtml.htmltools import *


# Pytest tests
def test_superstrip():
    assert superstrip("  hello   world  ") == "hello world"
    assert superstrip("\t\nhello\r\nworld\t") == "hello world"


def test_td_repr():
    td = Td("test")
    assert repr(td) == "Td: test"


def test_html_mod_parser():
    parser = HtmlModParser()
    assert parser is not None


if __name__ == "__main__":
    pytest.main()
