"""Tests for :mod:`pytigon_lib.schhtml.tags.table_tags` - <col>/<colgroup>."""

from unittest.mock import MagicMock

from pytigon_lib.schhtml.tags.table_tags import ColTag, TableTag


class _Parent:
    """Minimal TableTag stand-in exposing col_widths."""

    def __init__(self):
        self.col_widths = []


def _make_col(width, span=1):
    col = ColTag.__new__(ColTag)
    col.width = width
    col.span = span
    col.parent = _Parent()
    return col


class TestTableChildTags:
    def test_sections_and_cols_are_recognised(self):
        table = TableTag(None, MagicMock(), "table", {})
        for tag in ("thead", "tbody", "tfoot", "colgroup", "col"):
            assert tag in table.child_tags

    def test_col_widths_initialised(self):
        table = TableTag(None, MagicMock(), "table", {})
        assert table.col_widths == []


class TestColTag:
    def test_single_column_width(self):
        col = _make_col("120")
        col.close()
        assert col.parent.col_widths == ["120"]

    def test_span_repeats_width(self):
        col = _make_col("80", span=3)
        col.close()
        assert col.parent.col_widths == ["80", "80", "80"]

    def test_no_width_is_preserved_as_none(self):
        col = _make_col(None, span=2)
        col.close()
        assert col.parent.col_widths == [None, None]

    def test_parent_without_col_widths_is_safe(self):
        col = ColTag.__new__(ColTag)
        col.width = "10"
        col.span = 1
        col.parent = object()
        # Must not raise even when the parent does not track column widths.
        col.close()
