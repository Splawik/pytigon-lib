"""Tests for :mod:`pytigon_lib.schhtml.xlsxdc`."""

import io
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schhtml.basedc import BaseDc
from pytigon_lib.schhtml.xlsxdc import XlsxDc, XlsxDcinfo


@pytest.fixture
def _mock_temp(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    monkeypatch.setattr("pytigon_lib.schhtml.xlsxdc.get_temp_filename", lambda: tmp.name)
    yield tmp.name
    if os.path.exists(tmp.name):
        os.unlink(tmp.name)


class TestXlsxDcInit:
    def test_initialization_basic(self, _mock_temp):
        dc = XlsxDc()
        assert isinstance(dc, BaseDc)
        assert dc.handle_html_directly is True
        assert dc.document is not None
        assert dc.dc_info is not None

    def test_initialization_calc_only(self, _mock_temp):
        dc = XlsxDc(calc_only=True)
        assert dc.calc_only is True

    def test_initialization_with_dimensions(self, _mock_temp):
        dc = XlsxDc(width=10, height=20)
        assert dc.width == 10
        assert dc.height == 20
        assert dc.page_width == 10
        assert dc.page_height == 20

    def test_initialization_negative_width_is_replaced(self, _mock_temp):
        dc = XlsxDc(width=-5, height=500)
        assert dc.width == -1
        assert dc.height == 500

    def test_initialization_with_output_name(self, _mock_temp):
        dc = XlsxDc(output_name="test.xlsx")
        assert dc.output_name == "test.xlsx"

    def test_initialization_with_output_stream(self, _mock_temp):
        stream = io.BytesIO()
        dc = XlsxDc(output_stream=stream)
        assert dc.output_stream is stream

    def test_initialization_notify_callback(self, _mock_temp):
        callback = MagicMock()
        dc = XlsxDc(notify_callback=callback)
        callback.assert_called_once_with("start", {"dc": dc})

    def test_initialization_dc_info_type(self, _mock_temp):
        dc = XlsxDc()
        assert isinstance(dc.dc_info, XlsxDcinfo)

    def test_initialization_recording(self, _mock_temp):
        dc = XlsxDc(record=True)
        assert dc.rec is True

    def test_initialization_temp_file(self, _mock_temp):
        dc = XlsxDc()
        assert dc.temp_file_name is not None
        assert os.path.exists(dc.temp_file_name)


class TestXlsxDcMaps:
    def test_map_start_tag_contains_body(self, _mock_temp):
        dc = XlsxDc()
        assert "body" in dc.map_start_tag

    def test_map_start_tag_contains_div(self, _mock_temp):
        dc = XlsxDc()
        assert "div" in dc.map_start_tag

    def test_map_end_tag_contains_cells(self, _mock_temp):
        dc = XlsxDc()
        for tag in ("tr", "td", "th"):
            assert tag in dc.map_end_tag

    def test_map_end_tag_contains_block_tags(self, _mock_temp):
        dc = XlsxDc()
        for tag in ("h1", "h2", "h3", "h4", "h5", "h6", "p"):
            assert tag in dc.map_end_tag

    def test_map_end_tag_contains_img(self, _mock_temp):
        dc = XlsxDc()
        assert "img" in dc.map_end_tag

    def test_map_end_tag_contains_end_body(self, _mock_temp):
        dc = XlsxDc()
        assert "body" in dc.map_end_tag


class TestXlsxDcClose:
    def test_close_notify_callback(self, _mock_temp):
        dc = XlsxDc(output_name="test.xlsx")
        callback = MagicMock()
        dc.notify_callback = callback
        dc.document = MagicMock()
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = b"xlsx data"
            os.unlink = MagicMock()
            dc.close()
            callback.assert_called_once_with("end", {"dc": dc})

    def test_close_saves_to_stream(self, _mock_temp):
        stream = io.BytesIO()
        with patch.object(XlsxDc, "notify_callback", create=True):
            dc = XlsxDc(output_stream=stream)
            dc.document = MagicMock()
            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = b"xlsx data"
                os.unlink = MagicMock()
                dc.close()
                assert len(stream.getvalue()) > 0

    def test_close_saves_to_file(self, _mock_temp):
        with patch.object(XlsxDc, "notify_callback", create=True):
            dc = XlsxDc(output_name="test.xlsx")
            dc.document = MagicMock()
            with patch("builtins.open", create=True) as mock_open:
                mock_open.return_value.__enter__.return_value.read.return_value = b"xlsx data"
                os.unlink = MagicMock()
                dc.close()
                dc.document.close.assert_called_once()


class TestXlsxDcAnnotate:
    def test_annotate_start_tag_dispatches(self, _mock_temp):
        dc = XlsxDc()
        element = MagicMock()
        element.tag = "body"
        element.parent = MagicMock()

        dc.map_start_tag["body"] = MagicMock()
        dc.annotate("start_tag", {"element": element})
        dc.map_start_tag["body"].assert_called_once_with(element, element.parent)

    def test_annotate_end_tag_dispatches(self, _mock_temp):
        dc = XlsxDc()
        element = MagicMock()
        element.tag = "p"
        element.parent = MagicMock()

        dc.map_end_tag["p"] = MagicMock()
        dc.annotate("end_tag", {"element": element})
        dc.map_end_tag["p"].assert_called_once_with(element, element.parent)

    def test_annotate_ignores_unknown_tag(self, _mock_temp):
        dc = XlsxDc()
        element = MagicMock()
        element.tag = "unknown"
        element.parent = MagicMock()
        dc.annotate("start_tag", {"element": element})
        dc.annotate("end_tag", {"element": element})

    def test_annotate_ignores_element_without_parent(self, _mock_temp):
        dc = XlsxDc()
        element = MagicMock()
        element.tag = "p"
        element.parent = None
        dc.annotate("start_tag", {"element": element})
        dc.annotate("end_tag", {"element": element})


class TestXlsxDcGetColor:
    def test_get_color_valid_hex(self, _mock_temp):
        dc = XlsxDc()
        result = dc._get_color("#ff0000")
        assert result is not None
        assert "FF" in result

    def test_get_color_empty(self, _mock_temp):
        dc = XlsxDc()
        assert dc._get_color("") is None

    def test_get_color_none(self, _mock_temp):
        dc = XlsxDc()
        assert dc._get_color(None) is None


class TestXlsxDcInfo:
    def test_initialization(self, _mock_temp):
        dc = XlsxDc()
        info = XlsxDcinfo(dc)
        assert info.dc is dc

    def test_get_text_height(self, _mock_temp):
        dc = XlsxDc()
        info = XlsxDcinfo(dc)
        assert info.get_text_height("test", 0) == 1
