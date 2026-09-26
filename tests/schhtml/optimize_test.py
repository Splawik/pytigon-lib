"""Tests for the optional memory optimized table containers."""

import sys

import pytest

from pytigon_lib.schhtml import htmlviewer
from pytigon_lib.schhtml.htmltools import Td
from pytigon_lib.schhtml.optimize import (
    OptimizedRow,
    OptimizedTable,
    TdView,
    optimize_table,
)


def build_table():
    children = {"1": {"tag": "b", "attrs": {"x": "1"}}}
    return [
        [Td("A:10/2", {"bgcolor": "#fff"}), Td("B", {}), Td(None, {"a": "b"})],
        [Td("C", {"align": "center"}, children), Td("D", {}), Td("E", {})],
    ]


class TestPurePythonOptimizeTable:
    def test_values_are_preserved(self):
        table = optimize_table(build_table())
        assert isinstance(table, OptimizedTable)
        assert len(table) == 2
        assert table.num_rows == 2
        assert table.num_cols == 3
        assert table[0][0].data == "A:10/2"
        assert table[0][0].attrs == {"bgcolor": "#fff"}
        assert table[0][1].data == "B"
        assert table[0][2].data is None

    def test_children_objects_are_not_converted(self):
        table = optimize_table(build_table())
        children = table[1][0].children
        assert isinstance(children, dict)
        assert children["1"]["tag"] == "b"

    def test_cell_is_td_compatible(self):
        table = optimize_table(build_table())
        for row in table:
            for cell in row:
                assert isinstance(cell, Td)
        assert repr(table[0][0]) == "Td: A:10/2"
        assert table[0][0].attr == ""

    def test_negative_and_slice_indexing(self):
        table = optimize_table(build_table())
        assert table[-1][-1].data == "E"
        rows = table[1:]
        assert len(rows) == 1
        assert isinstance(rows[0], OptimizedRow)
        assert [cell.data for cell in table[0][1:]] == ["B", None]

    def test_iteration_and_len(self):
        table = optimize_table(build_table())
        assert [cell.data for cell in table[0]] == ["A:10/2", "B", None]
        assert len(table[0]) == 3

    def test_data_mutation_is_written_through(self):
        table = optimize_table(build_table())
        table[0][0].data = "changed"
        assert table[0][0].data == "changed"

    def test_direct_tdview_constructor(self):
        cell = TdView("x", {"k": "v"}, ["c"])
        assert cell.data == "x"
        assert cell.attrs == {"k": "v"}
        assert cell.children == ["c"]
        assert isinstance(cell, Td)

    def test_empty_and_none(self):
        assert optimize_table(None) is None
        empty = optimize_table([])
        assert isinstance(empty, OptimizedTable)
        assert len(empty) == 0


class TestPyArrowOptimizeTable:
    def test_parity_with_pure_backend(self):
        pa = pytest.importorskip("pyarrow")
        assert pa is not None
        from pytigon_lib.schhtml.optimize_max import optimize_table as pa_optimize

        table = pa_optimize(build_table())
        assert isinstance(table, OptimizedTable)
        assert table[0][0].data == "A:10/2"
        assert table[0][0].attrs == {"bgcolor": "#fff"}
        assert table[0][2].data is None
        assert table[1][0].children["1"]["tag"] == "b"
        assert repr(table[1][0]) == "Td: C"

    def test_write_through_overrides_arrow_column(self):
        pytest.importorskip("pyarrow")
        from pytigon_lib.schhtml.optimize_max import optimize_table as pa_optimize

        table = pa_optimize(build_table())
        table[0][1].data = "new"
        assert table[0][1].data == "new"
        assert table[0][0].data == "A:10/2"

    def test_non_string_data_falls_back(self):
        pytest.importorskip("pyarrow")
        from pytigon_lib.schhtml.optimize_max import optimize_table as pa_optimize

        assert pa_optimize([[Td(123), Td("x")]]) is None


class TestTdataFromHtmlOptimization:
    def _patch_parser(self, monkeypatch, tdata_tab):
        class StubParser:
            def __init__(self, *args, **kwargs):
                self.tdata_tab = tdata_tab

            def set_http_object(self, http):
                pass

            def feed(self, html):
                pass

            def close(self):
                pass

        class StubDc:
            def __init__(self, *args, **kwargs):
                pass

        monkeypatch.setattr(htmlviewer, "HtmlViewerParser", StubParser)
        monkeypatch.setattr(htmlviewer, "PdfDc", StubDc)
        monkeypatch.setattr(htmlviewer, "OPTIMIZE", None)
        monkeypatch.setattr(htmlviewer, "_OPTIMIZE_CHECKED", False)

    def test_returns_optimized_table(self, monkeypatch):
        self._patch_parser(monkeypatch, [([[Td("A"), Td("B")]], "ctrl-table", {})])
        tab = htmlviewer.tdata_from_html("<table></table>", None)
        assert isinstance(tab, OptimizedTable)
        assert tab[0][0].data == "A"

    def test_optimize_disabled_keeps_plain_table(self, monkeypatch):
        self._patch_parser(monkeypatch, [([[Td("A"), Td("B")]], "ctrl-table", {})])
        tab = htmlviewer.tdata_from_html("<table></table>", None, optimize=False)
        assert isinstance(tab[0][0], Td)
        assert not isinstance(tab, OptimizedTable)

    def test_falls_back_when_pyarrow_backend_missing(self, monkeypatch):
        self._patch_parser(monkeypatch, [([[Td("A"), Td("B")]], "ctrl-table", {})])
        monkeypatch.setitem(sys.modules, "pytigon_lib.schhtml.optimize_max", None)
        tab = htmlviewer.tdata_from_html("<table></table>", None)
        assert isinstance(tab, OptimizedTable)
        assert type(tab).__module__ == "pytigon_lib.schhtml.optimize"
        assert tab[0][1].data == "B"

    def test_returns_none_for_missing_table(self, monkeypatch):
        self._patch_parser(monkeypatch, [])
        assert htmlviewer.tdata_from_html("<table></table>", None) is None
