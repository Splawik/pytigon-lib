import datetime
import sys
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schdjangoext.import_from_db import (
    CACHE,
    DBFinder,
    DBModuleLoader,
    DBPackageLoader,
    ModuleStruct,
    add_to_cache,
    func_from_func_content,
    get_from_cache,
    get_fun_from_db_field,
    in_cache,
    run_code_from_db_field,
)


class TestCacheFunctions:
    def setup_method(self):
        CACHE.clear()

    def test_in_cache_missing_key(self):
        assert in_cache("missing_key") is False

    def test_add_to_cache_and_retrieve(self):
        add_to_cache("key1", "value1")
        result = get_from_cache("key1")
        assert result == "value1"

    def test_in_cache_no_timeout(self):
        add_to_cache("key1", "value1")
        with patch("pytigon_lib.schdjangoext.import_from_db._get_setting", return_value=0):
            assert in_cache("key1") is True

    def test_in_cache_not_expired(self):
        add_to_cache("key1", "value1")
        with patch("pytigon_lib.schdjangoext.import_from_db._get_setting", return_value=99999):
            assert in_cache("key1") is True

    def test_in_cache_expired(self):
        old_time = datetime.datetime.now() - datetime.timedelta(seconds=100)
        CACHE["key1"] = ("value", old_time)
        with patch("pytigon_lib.schdjangoext.import_from_db._get_setting", return_value=1):
            assert in_cache("key1") is False

    def test_get_from_cache_missing(self):
        assert get_from_cache("nonexistent") is None


class TestFuncFromFuncContent:
    def test_simple_function(self):
        result = func_from_func_content("myfunc", "return 42", None)
        assert "def myfunc():" in result
        assert "    return 42" in result

    def test_function_with_args(self):
        result = func_from_func_content("myfunc", "return x + y", ["x", "y"])
        assert "def myfunc(x,y):" in result

    def test_multiline_content(self):
        result = func_from_func_content("myfunc", "a = 1\nreturn a", None)
        assert "\n    a = 1" in result
        assert "\n    return a" in result or "return a" in result


class TestDBFinder:
    def test_finds_dbmodule_short_path(self):
        spec = DBFinder.find_spec("dbmodule.app.model")
        assert spec is not None

    def test_finds_dbmodule_long_path(self):
        spec = DBFinder.find_spec("dbmodule.app.model.sub.func")
        assert spec is not None

    def test_finds_dbmodule_package(self):
        spec = DBFinder.find_spec("dbmodule.app")
        assert spec is not None

    def test_non_dbmodule_returns_none(self):
        spec = DBFinder.find_spec("regular.module.name")
        assert spec is None


class TestDBModuleLoader:
    def test_get_filename(self):
        loader = DBModuleLoader()
        filename = loader.get_filename("dbmodule.app.model.func")
        assert ".dbpy" in filename

    def test_create_module(self):
        loader = DBModuleLoader()
        spec = MagicMock()
        spec.name = "dbmodule.test.module"
        mod = loader.create_module(spec)
        assert mod.__name__ == "dbmodule.test.module"
        assert "dbmodule" in mod.__package__


class TestDBPackageLoader:
    def test_exec_module_sets_path(self):
        module = MagicMock()
        module.__spec__ = MagicMock()
        module.__spec__.origin = "/path/to/__init__.dbpy"
        DBPackageLoader.exec_module(module)
        assert module.__path__ is not None


class TestModuleStruct:
    def test_module_struct_combines_globals_and_locals(self):
        g = {"g_key": "g_val"}
        l = {"l_key": "l_val"}
        ms = ModuleStruct(g, l)
        assert ms.g_key == "g_val"
        assert ms.l_key == "l_val"


class TestGetFunFromDbField:
    def test_exec_mode_with_def(self):
        base_obj = MagicMock()
        code = "def my_func():\n    return 42"
        base_obj.my_field = code
        with patch("pytigon_lib.schdjangoext.import_from_db._get_setting", return_value="exec"):
            mock_result = {"my_func": lambda: 42}
            with patch("pytigon_lib.schdjangoext.import_from_db._safe_exec", return_value=mock_result) as mock_exec:
                fun = get_fun_from_db_field("src1", base_obj, "my_func")
                assert fun is not None
                assert mock_exec.called

    def test_exec_mode_without_def(self):
        base_obj = MagicMock()
        base_obj.my_field = "return 99"
        with patch("pytigon_lib.schdjangoext.import_from_db._get_setting", return_value="exec"):
            with patch("pytigon_lib.schdjangoext.import_from_db._safe_exec", return_value={"my_field": lambda: 99}):
                fun = get_fun_from_db_field("src2", base_obj, "my_field")
                assert callable(fun)
                assert fun() == 99

    def test_empty_field_returns_none(self):
        base_obj = MagicMock()
        base_obj.my_field = ""
        result = get_fun_from_db_field("src3", base_obj, "my_field")
        assert result is None


class TestRunCodeFromDbField:
    def test_run_with_args(self):
        base_obj = MagicMock()
        base_obj.my_field = "def my_func(x, y):\n    return x + y\n"
        with patch("pytigon_lib.schdjangoext.import_from_db.get_fun_from_db_field", return_value=lambda x, y: x + y):
            result = run_code_from_db_field("src4", base_obj, "my_field", x=3, y=7)
            assert result == 10

    def test_no_function_returns_none(self):
        base_obj = MagicMock()
        base_obj.my_field = ""
        with patch("pytigon_lib.schdjangoext.import_from_db.get_fun_from_db_field", return_value=None):
            result = run_code_from_db_field("src5", base_obj, "my_field")
            assert result is None
