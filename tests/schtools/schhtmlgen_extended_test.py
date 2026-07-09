"""Tests for :mod:`pytigon_lib.schtools.schhtmlgen`."""

import pytest

from pytigon_lib.schtools.schhtmlgen import Html, make_start_tag


class TestHtml:
    def test_create_element(self):
        elem = Html("div")
        assert elem.name == "div"
        assert elem.children == []
        assert elem.value is None

    def test_set_value(self):
        elem = Html("p")
        elem.setvalue("Hello world")
        assert elem.value == "Hello world"

    def test_set_attr(self):
        elem = Html("div")
        elem.setattr('class="container"')
        assert elem.attr == 'class="container"'

    def test_append_string_child(self):
        parent = Html("div")
        child = parent.append("span")
        assert isinstance(child, Html)
        assert child.name == "span"
        assert len(parent.children) == 1

    def test_append_html_child(self):
        parent = Html("div")
        child = Html("p")
        result = parent.append(child)
        assert result is child
        assert len(parent.children) == 1

    def test_append_with_attr(self):
        parent = Html("div")
        child = parent.append("span", 'class="highlight"')
        assert child.attr == 'class="highlight"'

    def test_dump_simple(self):
        elem = Html("div")
        assert elem.dump() == "<div></div>"

    def test_dump_with_value(self):
        elem = Html("p")
        elem.setvalue("Text")
        assert elem.dump() == "<p>Text</p>"

    def test_dump_with_callable_value(self):
        elem = Html("p")
        elem.setvalue(lambda: "dynamic")
        assert elem.dump() == "<p>dynamic</p>"

    def test_dump_with_attr(self):
        elem = Html("div")
        elem.setattr("class='foo'")
        assert elem.dump() == '<div class="foo"></div>'

    def test_dump_nested(self):
        parent = Html("div")
        child = parent.append("span")
        child.setvalue("nested")
        assert parent.dump() == "<div><span>nested</span></div>"

    def test_dump_deeply_nested(self):
        outer = Html("div")
        mid = outer.append("section")
        inner = mid.append("p")
        inner.setvalue("deep")
        assert outer.dump() == "<div><section><p>deep</p></section></div>"

    def test_dump_multiple_children(self):
        parent = Html("ul")
        for i in range(3):
            li = parent.append("li")
            li.setvalue(str(i))
        result = parent.dump()
        for i in range(3):
            assert f"<li>{i}</li>" in result


class TestMakeStartTag:
    def test_simple_tag(self):
        result = make_start_tag("div", {})
        assert result == "<div>"

    def test_tag_with_string_attrs(self):
        result = make_start_tag("input", {"type": "text", "name": "email"})
        assert 'type="text"' in result
        assert 'name="email"' in result

    def test_tag_with_none_attr(self):
        result = make_start_tag("button", {"disabled": None})
        assert "disabled" in result
        assert "disabled=" not in result

    def test_tag_with_mixed_attrs(self):
        result = make_start_tag("input", {"type": "checkbox", "checked": None})
        assert 'type="checkbox"' in result
        assert " checked>" in result or " checked " in result

    def test_empty_attrs(self):
        result = make_start_tag("br", {})
        assert result == "<br>"
