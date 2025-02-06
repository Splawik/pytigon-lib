from pytigon_lib.schtools.wiki import *

# Pytest tests
import pytest


def test_wiki_from_str():
    assert wiki_from_str("Hello World") == "HelloWorld"
    assert wiki_from_str("?test") == "est"
    assert wiki_from_str("") == "index"
    assert (
        wiki_from_str("a b c d e f g h i j k l m n o p q r s t u v w x y z")
        == "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    )


def test_make_href():
    assert "href='/schwiki/section/HelloWorld/view/?desc=Hello World'" in make_href(
        "Hello World", section="section"
    )
    assert "target='_top2'" in make_href("Hello World", new_win=True)
    assert "class='btn btn-secondary'" in make_href("Hello World", btn=True)


def test_wikify():
    assert (
        wikify("Hello [[World]]")
        == "Hello <a href='../../World/view/?desc=World' target='_self' class='schbtn' label='World'>World</a>"
    )
    assert (
        wikify("Hello [[^World]]")
        == "Hello <a href='../../World/view/?desc=World' target='_top2' class='schbtn' label='World'>World</a>"
    )
    assert (
        wikify("Hello [[#World]]")
        == "Hello <a href='../../World/view/?desc=World' target='_self' class='btn btn-secondary' label='World'>World</a>"
    )
    assert (
        wikify("Hello [[World;section]]")
        == "Hello <a href='/schwiki/section/World/view/?desc=World' target='_self' class='schbtn' label='World'>World</a>"
    )


if __name__ == "__main__":
    pytest.main()
