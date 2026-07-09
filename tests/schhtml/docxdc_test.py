"""Tests for :mod:`pytigon_lib.schhtml.docxdc`."""

import io
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from pytigon_lib.schhtml.atom import BrAtom
from pytigon_lib.schhtml.basedc import BaseDc
from pytigon_lib.schhtml.docxdc import DocxDc, DocxDcinfo


class TestDocxDcInit:
    def test_initialization_basic(self):
        dc = DocxDc()
        assert isinstance(dc, BaseDc)
        assert dc.handle_html_directly is True
        assert dc.document is not None
        assert dc.dc_info is not None

    def test_initialization_calc_only(self):
        dc = DocxDc(calc_only=True)
        assert dc.calc_only is True

    def test_initialization_with_dimensions(self):
        dc = DocxDc(width=10, height=20)
        assert dc.width == 10
        assert dc.height == 20
        assert dc.page_width == 10
        assert dc.page_height == 20

    def test_initialization_negative_width(self):
        dc = DocxDc(width=-1, height=500)
        assert dc.width == -1
        assert dc.height == 500

    def test_initialization_with_output_name(self):
        dc = DocxDc(output_name="test.docx")
        assert dc.output_name == "test.docx"

    def test_initialization_with_output_stream(self):
        stream = io.BytesIO()
        dc = DocxDc(output_stream=stream)
        assert dc.output_stream is stream

    def test_initialization_with_template(self):
        dc = DocxDc(docx_template_path=None)
        assert dc.document is not None

    def test_initialization_notify_callback(self):
        callback = MagicMock()
        dc = DocxDc(notify_callback=callback)
        callback.assert_called_once_with("start", {"dc": dc})

    def test_initialization_dc_info_type(self):
        dc = DocxDc()
        assert isinstance(dc.dc_info, DocxDcinfo)

    def test_initialization_recording(self):
        dc = DocxDc(record=True)
        assert dc.rec is True


class TestDocxDcMargins:
    def test_set_margins_updates_body_dimensions(self):
        dc = DocxDc(width=8.5, height=11)
        dc.set_margins(1.0, 1.0, 1.0, 1.0)
        assert dc.body_width == 8.5 - 1.0 - 1.0
        assert dc.body_height == 11 - 1.0 - 1.0

    def test_set_margins_different_values(self):
        dc = DocxDc(width=8.5, height=11)
        dc.set_margins(0.5, 0.75, 0.5, 0.75)
        assert dc.body_width == pytest.approx(8.5 - 0.75 - 0.75)
        assert dc.body_height == pytest.approx(11 - 0.5 - 0.5)


class TestDocxDcMap:
    def test_map_contains_body(self):
        dc = DocxDc()
        assert "body" in dc.map

    def test_map_contains_p(self):
        dc = DocxDc()
        assert "p" in dc.map

    def test_map_contains_div(self):
        dc = DocxDc()
        assert "div" in dc.map

    def test_map_contains_table(self):
        dc = DocxDc()
        assert "table" in dc.map

    def test_map_contains_tr(self):
        dc = DocxDc()
        assert "tr" in dc.map

    def test_map_contains_td(self):
        dc = DocxDc()
        assert "td" in dc.map

    def test_map_contains_th(self):
        dc = DocxDc()
        assert "th" in dc.map

    def test_map_contains_heading_tags(self):
        dc = DocxDc()
        for tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            assert tag in dc.map


class TestDocxDcAnnotate:
    def test_annotate_end_tag_dispatches(self):
        dc = DocxDc()
        element = MagicMock()
        element.tag = "p"
        parent = MagicMock()
        element.parent = parent

        dc.map["p"] = MagicMock()
        dc.annotate("end_tag", {"element": element})
        dc.map["p"].assert_called_once_with(element, parent)

    def test_annotate_ignores_unknown_tag(self):
        dc = DocxDc()
        element = MagicMock()
        element.tag = "unknown"
        element.parent = MagicMock()

        dc.annotate("end_tag", {"element": element})


class TestDocxDcClose:
    def test_close_notify_callback(self):
        dc = DocxDc(output_name="test.docx")
        callback = MagicMock()
        dc.notify_callback = callback
        dc.close()
        callback.assert_called_once_with("end", {"dc": dc})

    def test_close_saves_to_stream(self):
        stream = io.BytesIO()
        with patch.object(DocxDc, "notify_callback", create=True):
            dc = DocxDc(output_stream=stream)
            dc.document = MagicMock()
            dc.close()
            dc.document.save.assert_called_once_with(stream)

    def test_close_saves_to_output_name(self):
        with patch.object(DocxDc, "notify_callback", create=True):
            dc = DocxDc(output_name="test.docx")
            dc.document = MagicMock()
            dc.close()
            dc.document.save.assert_called_once_with("test.docx")


class TestDocxDcHandleWidthHeight:
    def test_handle_width_percent(self):
        dc = DocxDc(width=8.5, height=11)
        dc.set_margins(1, 1, 1, 1)
        element = MagicMock()
        element.attrs = {"width": "50%"}
        w, h = dc._handle_width_and_height(element)
        assert w is not None

    def test_handle_width_px(self):
        dc = DocxDc(width=8.5, height=11)
        dc.set_margins(1, 1, 1, 1)
        element = MagicMock()
        element.attrs = {"width": "300px"}
        w, h = dc._handle_width_and_height(element)
        assert w == 1.0

    def test_handle_height_px(self):
        dc = DocxDc(width=8.5, height=11)
        dc.set_margins(1, 1, 1, 1)
        element = MagicMock()
        element.attrs = {"height": "300px"}
        w, h = dc._handle_width_and_height(element)
        assert h == 1.0

    def test_handle_no_dimensions(self):
        dc = DocxDc(width=8.5, height=11)
        element = MagicMock()
        element.attrs = {}
        w, h = dc._handle_width_and_height(element)
        assert w is None
        assert h is None


class TestDocxDcInfo:
    def test_initialization(self):
        dc = DocxDc()
        info = DocxDcinfo(dc)
        assert info.dc is dc

    def test_get_text_height(self):
        dc = DocxDc()
        info = DocxDcinfo(dc)
        assert info.get_text_height("test", 0) == 1
