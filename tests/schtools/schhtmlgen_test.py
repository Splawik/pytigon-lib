from pytigon_lib.schtools.schhtmlgen import *

# Pytest tests
import pytest


def test_html_dump():
    html = Html("div", 'class="container"')
    html.append("p", 'class="text"').setvalue("Hello, World!")
    assert (
        html.dump() == '<div class="container"><p class="text">Hello, World!</p></div>'
    )


def test_make_start_tag():
    attrs = {"class": "container", "id": "main"}
    assert make_start_tag("div", attrs) == '<div class="container" id="main">'


def test_itemplate_gen():
    ihtml = "<div>[{ message }]</div>"
    template = ITemplate(ihtml)
    result = template.gen({"message": "Hello, World!"})
    assert "<div>Hello, World!</div>" in result


if __name__ == "__main__":
    pytest.main()
