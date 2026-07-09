"""Tests for :mod:`pytigon_lib.schspreadsheet.ooxml_process` utility functions."""

import datetime

import pytest

from pytigon_lib.schspreadsheet.ooxml_process import (
    SECTION_WIDTH,
    col_row,
    date_to_float,
    filter_attr,
    key_for_addr,
    make_col_row,
    transform_str,
)


class TestTransformStr:
    def test_triple_star_to_double_quote(self):
        assert transform_str("a***b") == 'a"b'

    def test_double_star_to_single_quote(self):
        assert transform_str("a**b") == "a'b"

    def test_both(self):
        result = transform_str("a***b**c")
        assert result == "a\"b'c"

    def test_no_special_chars(self):
        assert transform_str("hello") == "hello"

    def test_empty_string(self):
        assert transform_str("") == ""


class TestFilterAttr:
    def test_exact_match(self):
        from unittest.mock import MagicMock

        items = []
        for i in range(3):
            m = MagicMock()
            m.attrib = {"r": f"A{i}"}
            items.append(m)
        result = filter_attr(items, "r", "A1")
        assert len(result) == 1
        assert result[0].attrib["r"] == "A1"

    def test_suffix_wildcard(self):
        from unittest.mock import MagicMock

        m = MagicMock()
        m.attrib = {"name": "test_value"}
        result = filter_attr([m], "name", "*value")
        assert len(result) == 1

    def test_prefix_wildcard(self):
        from unittest.mock import MagicMock

        m = MagicMock()
        m.attrib = {"name": "prefix_suffix"}
        result = filter_attr([m], "name", "prefix*")
        assert len(result) == 1

    def test_contains_wildcard(self):
        from unittest.mock import MagicMock

        m = MagicMock()
        m.attrib = {"name": "abc_mid_def"}
        result = filter_attr([m], "name", "*mid*")
        assert len(result) == 1

    def test_no_match(self):
        from unittest.mock import MagicMock

        m = MagicMock()
        m.attrib = {"name": "value"}
        result = filter_attr([m], "name", "other")
        assert len(result) == 0

    def test_missing_attr(self):
        from unittest.mock import MagicMock

        m = MagicMock()
        m.attrib = {"other": "value"}
        result = filter_attr([m], "name", "value")
        assert len(result) == 0

    def test_empty_list(self):
        result = filter_attr([], "r", "A1")
        assert result == []


class TestColRow:
    def test_single_letter(self):
        col, row, idx = col_row("A1")
        assert col == "A"
        assert row == 1
        assert idx == 1

    def test_single_letter_large_row(self):
        col, row, idx = col_row("B99")
        assert col == "B"
        assert row == 99
        assert idx == 2

    def test_double_letter(self):
        col, row, idx = col_row("AA10")
        assert col == "AA"
        assert row == 10
        assert idx == 27

    def test_z_column(self):
        col, row, idx = col_row("Z1")
        assert col == "Z"
        assert row == 1
        assert idx == 26

    def test_ab_column(self):
        col, row, idx = col_row("AB5")
        assert col == "AB"
        assert row == 5
        assert idx == 28

    def test_invalid_address(self):
        with pytest.raises(ValueError, match="Invalid Excel address"):
            col_row("A")

    def test_lowercase(self):
        col, _, _ = col_row("a1")
        assert col == "A"


class TestMakeColRow:
    def test_single_letter(self):
        result = make_col_row(1, 1)
        assert result == "A1"

    def test_column_b(self):
        result = make_col_row(2, 5)
        assert result == "B5"

    def test_double_letter(self):
        result = make_col_row(27, 3)
        assert result == "AA3"

    def test_ab_column(self):
        result = make_col_row(28, 1)
        assert result == "AB1"

    def test_roundtrip(self):
        for addr in ("A1", "B20", "Z100", "AA5", "AZ99"):
            col, row, _ = col_row(addr)
            result = make_col_row(col_row("Z1")[2] if col == "Z" else addr.count("A") or 27, row)
            addr2 = make_col_row(col_row(addr)[2], row)
            assert addr2 == addr.upper()


class TestKeyForAddr:
    def test_row_major_order(self):
        k1 = key_for_addr("A1")
        k2 = key_for_addr("B1")
        k3 = key_for_addr("A2")
        assert k1 < k2 < k3

    def test_same_row(self):
        k1 = key_for_addr("A10")
        k2 = key_for_addr("Z10")
        assert k1 < k2


class TestDateToFloat:
    def test_epoch_start(self):
        d = datetime.datetime(1899, 12, 30)
        result = date_to_float(d)
        assert result == 0.0

    def test_one_day_later(self):
        d = datetime.datetime(1899, 12, 31)
        result = date_to_float(d)
        assert result == 1.0

    def test_modern_date(self):
        d = datetime.datetime(2024, 1, 1)
        result = date_to_float(d)
        assert result > 44000
