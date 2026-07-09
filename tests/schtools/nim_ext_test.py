"""Tests for :mod:`pytigon_lib.schtools.nim_ext`."""

import json
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schtools.nim_ext import Module, def_module_function


class TestModule:
    def test_module_is_instantiable(self):
        m = Module()
        assert isinstance(m, Module)


class TestDefModuleFunction:
    @patch("pytigon_lib.schtools.nim_ext.ffi")
    def test_def_function_type_ii(self, mock_ffi):
        module = Module()
        lib = MagicMock()
        lib.fun_ii = MagicMock(return_value=42)

        def_module_function(module, lib, "test_ii", "ii", 1)
        result = module.test_ii(10)
        lib.fun_ii.assert_called_once_with(1, 10)
        assert result == 42

    @patch("pytigon_lib.schtools.nim_ext.ffi")
    def test_def_function_type_ff(self, mock_ffi):
        module = Module()
        lib = MagicMock()
        lib.fun_ff = MagicMock(return_value=3.14)

        def_module_function(module, lib, "test_ff", "ff", 2)
        result = module.test_ff(1.5)
        lib.fun_ff.assert_called_once_with(2, 1.5)
        assert result == 3.14

    @patch("pytigon_lib.schtools.nim_ext.ffi")
    def test_def_function_type_vi(self, mock_ffi):
        module = Module()
        lib = MagicMock()
        lib.fun_vi = MagicMock(return_value=0)

        def_module_function(module, lib, "test_vi", "vi", 3)
        result = module.test_vi()
        lib.fun_vi.assert_called_once_with(3)
        assert result == 0

    @patch("pytigon_lib.schtools.nim_ext.ffi")
    def test_def_function_type_si(self, mock_ffi):
        module = Module()
        lib = MagicMock()
        lib.fun_si = MagicMock(return_value=5)

        def_module_function(module, lib, "test_si", "si", 4)
        result = module.test_si("hello")
        lib.fun_si.assert_called_once_with(4, b"hello")
        assert result == 5

    @patch("pytigon_lib.schtools.nim_ext.ffi")
    def test_def_function_type_jj(self, mock_ffi):
        module = Module()
        lib = MagicMock()
        lib.fun_jj = MagicMock(return_value=json.dumps({"result": "ok"}).encode("utf-8"))
        mock_ffi.string = MagicMock(return_value=json.dumps({"result": "ok"}).encode("utf-8"))

        def_module_function(module, lib, "test_jj", "jj", 5)
        result = module.test_jj(key="value")
        assert result == {"result": "ok"}

    def test_unsupported_type(self):
        module = Module()
        lib = MagicMock()
        with pytest.raises(ValueError, match="Unsupported type signature"):
            def_module_function(module, lib, "bad", "xx", 0)

    @patch("pytigon_lib.schtools.nim_ext.ffi")
    def test_def_function_ss_creates_both_variants(self, mock_ffi):
        module = Module()
        lib = MagicMock()
        ret_val = b"hello decoded"
        lib.fun_ss = MagicMock(return_value=ret_val)
        mock_ffi.string = MagicMock(return_value=b"hello decoded")

        def_module_function(module, lib, "test_ss", "ss", 6)
        assert hasattr(module, "test_ss")
        assert hasattr(module, "test_ss_str")
