"""Extra tests for :mod:`pytigon_lib.schtable.table`."""
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


class TestTableExtra:
    def test_init_auto_cols(self):
        t = Table()
        assert t.auto_cols == []

    def test_init_col_length(self):
        t = Table()
        assert t.col_length == [0]

    def test_init_col_names(self):
        t = Table()
        assert t.col_names == ["ID"]

    def test_init_default_rec(self):
        t = Table()
        assert t.default_rec == [0]

    def test_info_is_json_string(self):
        t = Table()
        info = t._info()
        assert isinstance(info, str)
        assert "auto_cols" in info
        assert "col_length" in info
        assert "col_names" in info
        assert "col_types" in info
        assert "default_rec" in info


class TestTablePyExtra:
    @pytest.fixture
    def table(self):
        return TablePy(
            table=[["Alice", 30], ["Bob", 25], ["Charlie", 35]],
            col_names=["Name", "Age"],
            col_typ=["str", "int"],
            col_length=[20, 5],
            default_rec=["", 0],
        )

    def test_count_after_insert(self, table):
        table.insert_rec(["Dave", 40])
        assert table.count() == 4

    def test_count_after_delete(self, table):
        table.delete_rec(0)
        assert table.count() == 2

    def test_sort_single_column(self, table):
        page = table.page(0, sort="Name")
        names = [r[1] for r in page]
        assert names == sorted(names)

    def test_sort_descending_single(self, table):
        page = table.page(0, sort="-Name")
        names = [r[1] for r in page]
        assert names == sorted(names, reverse=True)

    def test_sort_numeric(self, table):
        page = table.page(0, sort="Age")
        ages = [r[2] for r in page]
        assert ages == sorted(ages)

    def test_update_preserves_other_records(self, table):
        table.update_rec([0, "AliceNew", 31])
        page = table.page(0)
        assert page[1][1] == "Bob"

    def test_command_default_page(self, table):
        result = table.command({})
        assert "Alice" in result

    def test_command_info(self, table):
        result = table.command({"cmd": CMD_INFO})
        assert "Name" in result
        assert "ID" in result

    def test_command_count(self, table):
        result = table.command({"cmd": CMD_COUNT})
        assert "3" in result

    def test_command_sync(self, table):
        result = table.command({
            "cmd": CMD_SYNC,
            "update": "[]",
            "insert": "[]",
            "delete": "[]",
        })
        assert result == "OK"

    def test_command_exec_error(self, table):
        result = table.command({"cmd": CMD_EXEC, "value": {}})
        assert isinstance(result, str)

    def test_command_exec_dict_return(self):
        class ExecTable(TablePy):
            def exec_command(self, value):
                return {"status": "ok"}

        t = ExecTable(
            table=[],
            col_names=["Col1"],
            col_typ=["str"],
            col_length=[10],
            default_rec=[""],
        )
        result = t.command({"cmd": CMD_EXEC, "value": {}})
        assert "status" in result


class TestStrCmpExtra:
    def test_single_sort_equal_values(self):
        x = ["same", "a"]
        y = ["same", "b"]
        assert str_cmp(x, y, ((0, 1),)) == 0

    def test_two_level_sort_first_diff(self):
        x = ["a", "z"]
        y = ["b", "a"]
        assert str_cmp(x, y, ((0, 1), (1, 1))) < 0

    def test_two_level_sort_second_diff(self):
        x = ["a", "a"]
        y = ["a", "b"]
        assert str_cmp(x, y, ((0, 1), (1, 1))) < 0

    def test_three_level_sort(self):
        x = ["a", "b", "x"]
        y = ["a", "b", "a"]
        assert str_cmp(x, y, ((0, 1), (1, 1), (2, 1))) > 0

    def test_three_level_sort_equal(self):
        x = ["a", "b", "c"]
        y = ["a", "b", "c"]
        assert str_cmp(x, y, ((0, 1), (1, 1), (2, 1))) == 0

    def test_mixed_directions(self):
        x = ["a", 5, "c"]
        y = ["a", 10, "c"]
        assert str_cmp(x, y, ((0, 1), (1, -1), (2, 1))) > 0


class TestCommandConstants:
    def test_all_constants_distinct(self):
        constants = [CMD_INFO, CMD_PAGE, CMD_COUNT, CMD_SYNC, CMD_AUTO, CMD_RECASSTR, CMD_EXEC]
        assert len(set(constants)) == len(constants)
