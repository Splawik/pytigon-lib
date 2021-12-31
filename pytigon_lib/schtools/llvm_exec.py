import llvmlite.binding as llvm

llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()


def _create_execution_engine():
    target = llvm.Target.from_default_triple()
    target_machine = target.create_target_machine()
    backing_mod = llvm.parse_assembly("")
    engine = llvm.create_mcjit_compiler(backing_mod, target_machine)
    return engine


def _compile_ir(engine, llvm_ir):
    mod = llvm.parse_assembly(llvm_ir)
    mod.verify()
    engine.add_module(mod)
    engine.finalize_object()
    engine.run_static_constructors()
    return mod


ENGINE = _create_execution_engine()


def compile_str_to_module(llvm_ir):
    if type(llvm_ir) == str:
        try:
            mod = _compile_ir(ENGINE, llvm_ir)
        except Exception as e:
            print(e)
    else:
        for s in llvm_ir:
            mod = _compile_ir(ENGINE, s)


def compile_file_to_module(llvm_ir_path):
    if type(llvm_ir_path) == str:
        with open(llvm_ir_path, "rt") as f:
            compile_str_to_module(f.read())
    else:
        for s in llvm_ir_path:
            with open(s, "rt") as f:
                compile_str_to_module(f.read())


def get_function(name):
    func_ptr = ENGINE.get_function_address(name)
    return func_ptr
