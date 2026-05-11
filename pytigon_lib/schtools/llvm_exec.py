"""LLVM IR compilation and execution utilities.

Provides helpers to compile LLVM IR from strings or files and
retrieve function pointers from the JIT-compiled code.
"""

import llvmlite.binding as llvm

# Initialize LLVM components once at module load
llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()


def _create_execution_engine():
    """Create and return an LLVM MCJIT execution engine.

    Returns:
        An llvmlite execution engine instance.
    """
    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()
    backing_mod = llvm.parse_assembly("")
    engine = llvm.create_mcjit_compiler(backing_mod, target_machine)
    return engine


def _compile_ir(engine, llvm_ir):
    """Parse, verify, and add an LLVM IR module to the engine.

    Args:
        engine: The execution engine.
        llvm_ir: LLVM IR source as a string.

    Returns:
        The compiled module.

    Raises:
        RuntimeError: If IR parsing or verification fails.
    """
    mod = llvm.parse_assembly(llvm_ir)
    mod.verify()
    engine.add_module(mod)
    engine.finalize_object()
    engine.run_static_constructors()
    return mod


# Global execution engine instance (shared across all compilations)
ENGINE = _create_execution_engine()


def compile_str_to_module(llvm_ir):
    """Compile LLVM IR from a string or list of strings.

    Args:
        llvm_ir: A string of LLVM IR or a list/tuple of strings.

    Returns:
        The compiled module (for a single string) or None (for lists).

    Raises:
        TypeError: If llvm_ir is not a string or iterable of strings.
        RuntimeError: If compilation fails.
    """
    if isinstance(llvm_ir, str):
        try:
            return _compile_ir(ENGINE, llvm_ir)
        except Exception as e:
            raise RuntimeError(f"Error compiling LLVM IR: {e}")
    elif isinstance(llvm_ir, (list, tuple)):
        for ir in llvm_ir:
            try:
                _compile_ir(ENGINE, ir)
            except Exception as e:
                raise RuntimeError(f"Error compiling LLVM IR: {e}")
    else:
        raise TypeError("Expected a string or list of strings for LLVM IR.")


def compile_file_to_module(llvm_ir_path):
    """Compile LLVM IR from a file or list of files.

    Args:
        llvm_ir_path: A file path or list/tuple of file paths.

    Returns:
        The compiled module (for a single file) or None (for lists).

    Raises:
        TypeError: If llvm_ir_path is not a string or iterable of strings.
        RuntimeError: If file reading or compilation fails.
    """
    if isinstance(llvm_ir_path, str):
        try:
            with open(llvm_ir_path, "rt") as f:
                return compile_str_to_module(f.read())
        except IOError as e:
            raise RuntimeError(f"Error reading file {llvm_ir_path}: {e}")
    elif isinstance(llvm_ir_path, (list, tuple)):
        for path in llvm_ir_path:
            try:
                with open(path, "rt") as f:
                    compile_str_to_module(f.read())
            except IOError as e:
                raise RuntimeError(f"Error reading file {path}: {e}")
    else:
        raise TypeError("Expected a string or list of strings for file paths.")


def get_function(name):
    """Get the address of a compiled function by its symbol name.

    Args:
        name: The function/symbol name to look up.

    Returns:
        The function pointer address as an integer.

    Raises:
        RuntimeError: If the function cannot be found.
    """
    try:
        func_ptr = ENGINE.get_function_address(name)
        return func_ptr
    except Exception as e:
        raise RuntimeError(f"Error getting function address for '{name}': {e}")
