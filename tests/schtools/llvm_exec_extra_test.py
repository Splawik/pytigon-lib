"""Additional tests for :mod:`pytigon_lib.schtools.llvm_exec` beyond llvm_exec_test.py."""

import pytest

from pytigon_lib.schtools.llvm_exec import (
    ENGINE,
    _compile_ir,
    _create_execution_engine,
    compile_file_to_module,
    compile_str_to_module,
    get_function,
)


class TestCompileStrToModuleExtra:
    def test_compile_multiple_modules_from_list(self):
        modules = [
            """
            define i32 @add(i32 %a, i32 %b) {
                %result = add i32 %a, %b
                ret i32 %result
            }
            """,
            """
            define i32 @sub(i32 %a, i32 %b) {
                %result = sub i32 %a, %b
                ret i32 %result
            }
            """,
        ]
        result = compile_str_to_module(modules)
        assert result is None
        add_ptr = get_function("add")
        sub_ptr = get_function("sub")
        assert add_ptr != 0
        assert sub_ptr != 0

    def test_compile_list_with_invalid_ir_raises(self):
        with pytest.raises(RuntimeError, match="Error compiling LLVM IR"):
            compile_str_to_module(["valid module\n", "invalid llvm ir"])

    def test_compile_from_tuple(self):
        modules = (
            """
            define i32 @mul(i32 %a, i32 %b) {
                %result = mul i32 %a, %b
                ret i32 %result
            }
            """,
        )
        result = compile_str_to_module(modules)
        assert result is None
        assert get_function("mul") != 0

    def test_invalid_type_raises_type_error(self):
        with pytest.raises(TypeError, match="Expected a string or list of strings"):
            compile_str_to_module(42)

    def test_invalid_type_dict_raises_type_error(self):
        with pytest.raises(TypeError, match="Expected a string or list of strings"):
            compile_str_to_module({"key": "value"})


class TestCompileFileToModuleExtra:
    def test_compile_multiple_files_from_list(self, tmp_path):
        ir1 = """
        define i32 @double(i32 %x) {
            %result = add i32 %x, %x
            ret i32 %result
        }
        """
        ir2 = """
        define i32 @triple(i32 %x) {
            %result1 = add i32 %x, %x
            %result2 = add i32 %result1, %x
            ret i32 %result2
        }
        """
        f1 = tmp_path / "a.ll"
        f2 = tmp_path / "b.ll"
        f1.write_text(ir1)
        f2.write_text(ir2)
        result = compile_file_to_module([str(f1), str(f2)])
        assert result is None
        assert get_function("double") != 0
        assert get_function("triple") != 0

    def test_compile_file_list_invalid_path_type(self):
        with pytest.raises(TypeError, match="Expected a string or list of strings"):
            compile_file_to_module(123)

    def test_empty_file_compiles(self, tmp_path):
        f = tmp_path / "empty.ll"
        f.write_text("")
        result = compile_file_to_module(str(f))
        assert result is not None


class TestGetFunctionExtra:
    def test_get_newly_compiled_function(self):
        ir = """
        define i32 @square(i32 %x) {
            %result = mul i32 %x, %x
            ret i32 %result
        }
        """
        compile_str_to_module(ir)
        ptr = get_function("square")
        assert isinstance(ptr, int)
        assert ptr != 0


class TestCreateExecutionEngine:
    def test_engine_is_sharable(self):
        engine = _create_execution_engine()
        assert engine is not None
        ir = """
        define i32 @shared_func(i32 %x) {
            ret i32 %x
        }
        """
        _compile_ir(engine, ir)
        assert engine.get_function_address("shared_func") != 0
