"""Tests for :mod:`pytigon_lib.schhtml.render_helpers`."""
import pytest

from pytigon_lib.schhtml.render_helpers import (
    RenderBase,
    RenderBackground,
    RenderBorder,
    RenderCellSpacing,
    RenderCellPadding,
    RenderMargin,
    RenderPadding,
)


class TestRenderBase:
    def test_init(self):
        class FakeParent:
            attrs = {}
            hover = False
            hover_css_attrs = {}

        rb = RenderBase(FakeParent())
        assert rb.parent is not None
        assert rb.rendered_attribs is None

    def test_get_size_no_attribs(self):
        class FakeParent:
            attrs = {}
            hover = False
            hover_css_attrs = {}

        rb = RenderBase(FakeParent())
        assert rb.get_size() == [0, 0, 0, 0]

    def test_render_no_attribs(self):
        class FakeParent:
            attrs = {}
            hover = False
            hover_css_attrs = {}

        rb = RenderBase(FakeParent())
        result = rb.render(None)
        assert result is None


class TestRenderBackground:
    def test_init(self):
        class FakeParent:
            attrs = {}
            hover = False
            hover_css_attrs = {}

        rb = RenderBackground(FakeParent())
        assert rb.rendered_attribs is not None
        assert "background-color" in rb.rendered_attribs

    def test_get_size(self):
        class FakeParent:
            attrs = {}
            hover = False
            hover_css_attrs = {}

        rb = RenderBackground(FakeParent())
        size = rb.get_size()
        assert size == [0, 0, 0, 0]


class TestRenderBorder:
    def test_init(self):
        class FakeParent:
            attrs = {}
            hover = False
            hover_css_attrs = {}

        rb = RenderBorder(FakeParent())
        assert rb.rendered_attribs is not None


class TestRenderCellSpacing:
    def test_init(self):
        class FakeParent:
            attrs = {}
            hover = False
            hover_css_attrs = {}

        rb = RenderCellSpacing(FakeParent())
        assert rb.rendered_attribs is not None


class TestRenderCellPadding:
    def test_init(self):
        class FakeParent:
            attrs = {}
            hover = False
            hover_css_attrs = {}

        rb = RenderCellPadding(FakeParent())
        assert rb.rendered_attribs is not None


class TestRenderMargin:
    def test_init(self):
        class FakeParent:
            attrs = {}
            hover = False
            hover_css_attrs = {}

        rb = RenderMargin(FakeParent())
        assert rb.rendered_attribs is not None


class TestRenderPadding:
    def test_init(self):
        class FakeParent:
            attrs = {}
            hover = False
            hover_css_attrs = {}

        rb = RenderPadding(FakeParent())
        assert rb.rendered_attribs is not None


class TestRenderHelpersAll:
    def test_all_classes_importable(self):
        assert RenderBase is not None
        assert RenderBackground is not None
        assert RenderBorder is not None
        assert RenderCellSpacing is not None
        assert RenderCellPadding is not None
        assert RenderMargin is not None
        assert RenderPadding is not None
