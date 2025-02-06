import llvmlite.binding as llvm

# Initialize LLVM components
llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()


def _create_execution_engine():
    """Create and return an LLVM execution engine."""
    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()
    backing_mod = llvm.parse_assembly("")
    engine = llvm.create_mcjit_compiler(backing_mod, target_machine)
    return engine


def _compile_ir(engine, llvm_ir):
    """Compile LLVM IR and return the module."""
    mod = llvm.parse_assembly(llvm_ir)
    mod.verify()
    engine.add_module(mod)
    engine.finalize_object()
    engine.run_static_constructors()
    return mod


# Global execution engine instance
ENGINE = _create_execution_engine()


def compile_str_to_module(llvm_ir):
    """Compile LLVM IR from a string or list of strings."""
    if isinstance(llvm_ir, str):
        try:
            return _compile_ir(ENGINE, llvm_ir)
        except Exception as e:
            print(f"Error compiling LLVM IR: {e}")
            raise
    elif isinstance(llvm_ir, (list, tuple)):
        for ir in llvm_ir:
            try:
                _compile_ir(ENGINE, ir)
            except Exception as e:
                print(f"Error compiling LLVM IR: {e}")
                raise
    else:
        raise TypeError("Expected a string or list of strings for LLVM IR.")


def compile_file_to_module(llvm_ir_path):
    """Compile LLVM IR from a file or list of files."""
    if isinstance(llvm_ir_path, str):
        try:
            with open(llvm_ir_path, "rt") as f:
                return compile_str_to_module(f.read())
        except Exception as e:
            print(f"Error reading or compiling file {llvm_ir_path}: {e}")
            raise
    elif isinstance(llvm_ir_path, (list, tuple)):
        for path in llvm_ir_path:
            try:
                with open(path, "rt") as f:
                    compile_str_to_module(f.read())
            except Exception as e:
                print(f"Error reading or compiling file {path}: {e}")
                raise
    else:
        raise TypeError("Expected a string or list of strings for file paths.")


def get_function(name):
    """Get the address of a compiled function by name."""
    try:
        func_ptr = ENGINE.get_function_address(name)
        return func_ptr
    except Exception as e:
        print(f"Error getting function address for {name}: {e}")
        raise
