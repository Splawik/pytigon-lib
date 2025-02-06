from pytigon_lib.schtools.llvm_exec import *

# Pytest tests
import pytest


def test_compile_str_to_module():
    llvm_ir = """
    define i32 @add(i32 %a, i32 %b) {
        %result = add i32 %a, %b
        ret i32 %result
    }
    """
    mod = compile_str_to_module(llvm_ir)
    assert mod is not None


def test_compile_file_to_module(tmp_path):
    llvm_ir = """
    define i32 @multiply(i32 %a, i32 %b) {
        %result = mul i32 %a, %b
        ret i32 %result
    }
    """
    file_path = tmp_path / "test.ll"
    file_path.write_text(llvm_ir)
    compile_file_to_module(str(file_path))


def test_get_function():
    llvm_ir = """
    define i32 @add(i32 %a, i32 %b) {
        %result = add i32 %a, %b
        ret i32 %result
    }
    """
    compile_str_to_module(llvm_ir)
    func_ptr = get_function("add")
    assert func_ptr is not None


def test_compile_str_to_module_error():
    with pytest.raises(Exception):
        compile_str_to_module("invalid llvm ir")


def test_compile_file_to_module_error(tmp_path):
    file_path = tmp_path / "nonexistent.ll"
    with pytest.raises(Exception):
        compile_file_to_module(str(file_path))


def test_get_function_error():
    fun = get_function("nonexistent_function")
    assert fun == 0
