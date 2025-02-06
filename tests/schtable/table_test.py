from pytigon_lib.schtable.table import *

# Pytest tests
import pytest


def test_table_py_page():
    table = TablePy(
        [[1, 2], [3, 4]], ["col1", "col2"], ["int", "int"], [10, 10], [0, 0]
    )
    assert table.page(0) == [[0, 1, 2], [1, 3, 4]]


def test_table_py_count():
    table = TablePy(
        [[1, 2], [3, 4]], ["col1", "col2"], ["int", "int"], [10, 10], [0, 0]
    )
    assert table.count() == 2


def test_table_py_insert_rec():
    table = TablePy(
        [[1, 2], [3, 4]], ["col1", "col2"], ["int", "int"], [10, 10], [0, 0]
    )
    table.insert_rec([2, 5, 6])
    assert table.tab == [[1, 2], [3, 4], [5, 6]]


def test_table_py_update_rec():
    table = TablePy(
        [[1, 2], [3, 4]], ["col1", "col2"], ["int", "int"], [10, 10], [0, 0]
    )
    table.update_rec([1, 5, 6])
    assert table.tab == [[1, 2], [5, 6]]


def test_table_py_delete_rec():
    table = TablePy(
        [[1, 2], [3, 4]], ["col1", "col2"], ["int", "int"], [10, 10], [0, 0]
    )
    table.delete_rec(0)
    assert table.tab == [[3, 4]]


def test_table_py_auto():
    table = TablePy(
        [[1, 2], [3, 4]], ["col1", "col2"], ["int", "int"], [10, 10], [0, 0]
    )
    assert table.auto("col1", ["col1", "col2"], [1, 2]) is None
