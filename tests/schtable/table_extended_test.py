"""Tests for :mod:`pytigon_lib.schtable.table`."""

import pytest

from pytigon_lib.schtable.table import (
    CMD_AUTO,
    CMD_COUNT,
    CMD_EXEC,
    CMD_INFO,
    CMD_PAGE,
    CMD_RECASSTR,
    CMD_SYNC,
    Table,
    TablePy,
    str_cmp,
)


class TestTable:
    def test_init_defaults(self):
        t = Table()
        assert t.auto_cols == []
        assert t.col_length == [0]
        assert t.col_names == ["ID"]
        assert t.col_types == ["int"]
        assert t.default_rec == [0]

    def test_info_returns_json(self):
        t = Table()
        result = t._info()
        assert isinstance(result, str)
        assert "auto_cols" in result
        assert "col_names" in result

    def test_command_info(self):
        t = Table()
        result = t.command({"cmd": CMD_INFO})
        assert isinstance(result, str)

    def test_command_page(self):
        t = Table()
        with pytest.raises(NotImplementedError):
            t.command({"cmd": CMD_PAGE, "nr": 1})

    def test_command_count(self):
        t = Table()
        with pytest.raises(NotImplementedError):
            t.command({"cmd": CMD_COUNT})

    def test_command_sync(self):
        t = Table()
        result = t.command({
            "cmd": CMD_SYNC,
            "update": "[]",
            "insert": "[]",
            "delete": "[]",
        })
        assert result == "OK"

    def test_command_sync_with_error(self):
        t = Table()

        class ErrorTable(Table):
            def update_rec(self, rec):
                raise ValueError("test error")

        et = ErrorTable()
        result = et.command({
            "cmd": CMD_SYNC,
            "update": '[["any"]]',
            "insert": "[]",
            "delete": "[]",
        })
        assert "error" in result

    def test_command_auto_no_impl(self):
        t = Table()
        with pytest.raises(NotImplementedError):
            t.command({
                "cmd": CMD_AUTO,
                "col_name": "test",
                "col_names": ["a", "b"],
                "rec": [1, 2, 3],
            })

    def test_command_rec_as_str(self):
        t = Table()
        with pytest.raises(NotImplementedError):
            t.command({"cmd": CMD_RECASSTR, "nr": "1"})

    def test_command_exec_no_impl(self):
        t = Table()
        result = t.command({"cmd": CMD_EXEC, "value": {}})
        assert result is not None

    def test_command_unknown_cmd(self):
        t = Table()
        result = t.command({"cmd": 999})
        assert result is None

    def test_command_default_cmd_page(self):
        t = Table()
        with pytest.raises(NotImplementedError):
            t.command({})

    def test_page_raises_not_implemented(self):
        t = Table()
        with pytest.raises(NotImplementedError):
            t.page(1)

    def test_count_raises_not_implemented(self):
        t = Table()
        with pytest.raises(NotImplementedError):
            t.count()

    def test_rec_as_str_raises_not_implemented(self):
        t = Table()
        with pytest.raises(NotImplementedError):
            t.rec_as_str(1)

    def test_insert_rec_raises_not_implemented(self):
        t = Table()
        with pytest.raises(NotImplementedError):
            t.insert_rec([])

    def test_update_rec_raises_not_implemented(self):
        t = Table()
        with pytest.raises(NotImplementedError):
            t.update_rec([])

    def test_delete_rec_raises_not_implemented(self):
        t = Table()
        with pytest.raises(NotImplementedError):
            t.delete_rec(1)

    def test_auto_raises_not_implemented(self):
        t = Table()
        with pytest.raises(NotImplementedError):
            t.auto("col", ["c1", "c2"], [])

    def test_exec_command_raises_not_implemented(self):
        t = Table()
        with pytest.raises(NotImplementedError):
            t.exec_command({})


class TestStrCmp:
    def test_compare_greater(self):
        x = ["a", "z"]
        y = ["a", "b"]
        assert str_cmp(x, y, ((0, 1),)) == 0
        assert str_cmp(x, y, ((1, 1),)) > 0

    def test_compare_less(self):
        x = ["a", "a"]
        y = ["a", "b"]
        assert str_cmp(x, y, ((1, 1),)) < 0

    def test_compare_equal(self):
        x = ["a", "b"]
        y = ["a", "b"]
        assert str_cmp(x, y, ((0, 1), (1, 1))) == 0

    def test_compare_descending(self):
        x = ["a", "a"]
        y = ["a", "b"]
        assert str_cmp(x, y, ((1, -1),)) > 0

    def test_compare_multi_level(self):
        x = ["a", "z", "a"]
        y = ["a", "z", "b"]
        assert str_cmp(x, y, ((0, 1), (1, 1), (2, 1))) < 0


class TestTablePy:
    @pytest.fixture
    def table(self):
        data = [
            ["Alice", 30],
            ["Bob", 25],
            ["Charlie", 35],
            ["Diana", 28],
        ]
        return TablePy(
            table=data,
            col_names=["Name", "Age"],
            col_typ=["str", "int"],
            col_length=[20, 5],
            default_rec=["", 0],
        )

    def test_init(self, table):
        assert table.col_names == ["ID", "Name", "Age"]
        assert table.col_types == ["int", "str", "int"]
        assert table.col_length == [0, 20, 5]
        assert table.default_rec == [0, "", 0]

    def test_count(self, table):
        assert table.count() == 4

    def test_count_empty(self):
        t = TablePy(table=[], col_names=[], col_typ=[], col_length=[], default_rec=[])
        assert t.count() == 0

    def test_page_no_sort(self, table):
        page = table.page(0)
        assert len(page) == 4
        assert page[0] == [0, "Alice", 30]
        assert page[3] == [3, "Diana", 28]

    def test_page_pagination(self, table):
        data = [["Item" + str(i), i] for i in range(300)]
        t = TablePy(
            table=data,
            col_names=["Name", "Age"],
            col_typ=["str", "int"],
            col_length=[20, 5],
            default_rec=["", 0],
        )
        page0 = t.page(0)
        assert len(page0) == 256
        page1 = t.page(1)
        assert len(page1) == 44

    def test_page_sort_ascending(self, table):
        page = table.page(0, sort="Name")
        names = [rec[1] for rec in page]
        assert names == sorted(names)

    def test_page_sort_descending(self, table):
        page = table.page(0, sort="-Name")
        assert len(page) == 4

    def test_insert_rec(self, table):
        table.insert_rec(["Eve", 22])
        assert table.count() == 5

    def test_update_rec(self, table):
        table.update_rec([0, "AliceNew", 31])
        page = table.page(0)
        assert page[0][1] == "AliceNew"
        assert page[0][2] == 31

    def test_delete_rec(self, table):
        table.delete_rec(0)
        assert table.count() == 3
        page = table.page(0)
        assert page[0][1] == "Bob"

    def test_command_info(self, table):
        result = table.command({"cmd": CMD_INFO})
        assert "Name" in result

    def test_command_page_no_sort(self, table):
        result = table.command({"cmd": CMD_PAGE, "nr": 0})
        assert "Alice" in result

    def test_command_sync_ok(self, table):
        result = table.command({
            "cmd": CMD_SYNC,
            "update": "[]",
            "insert": "[]",
            "delete": "[]",
        })
        assert result == "OK"

    def test_command_count(self, table):
        result = table.command({"cmd": CMD_COUNT})
        assert "4" in result


class TestConstants:
    def test_cmd_constants(self):
        assert CMD_INFO == 1
        assert CMD_PAGE == 2
        assert CMD_COUNT == 3
        assert CMD_SYNC == 4
        assert CMD_AUTO == 5
        assert CMD_RECASSTR == 6
        assert CMD_EXEC == 7
