import json
from cffi import FFI
import sys
import os

ffi = FFI()


class Module:
    pass


def def_module_function(module, lib, fun_name, t, n):
    if t == "jj":

        def tmp(**argv):
            nonlocal n
            ret = lib.fun_jj(n, json.dumps(argv).encode("utf-8"))
            ret_str = ffi.string(ret)
            return json.loads(ret_str)

        setattr(module, fun_name, tmp)
    elif t in "ii":

        def tmp(arg):
            nonlocal n
            return lib.fun_ii(n, arg)

        setattr(module, fun_name, tmp)
    elif t in "ff":

        def tmp(arg):
            nonlocal n
            return lib.fun_ff(n, arg)

        setattr(module, fun_name, tmp)
    elif t in "vi":

        def tmp():
            nonlocal n
            return lib.fun_vi(n)

        setattr(module, fun_name, tmp)
    elif t in "ss":

        def tmp(s):
            nonlocal n
            ret = lib.fun_ss(n, s)
            ret_str = ffi.string(ret)
            return ret_str

        setattr(module, fun_name, tmp)

        def tmp2(s):
            nonlocal n
            ret = lib.fun_ss(n, s.encode("utf-8"))
            ret_str = ffi.string(ret)
            return ret_str.decode("utf-8")

        setattr(module, fun_name + "_str", tmp2)
    elif t in "si":

        def tmp(s):
            nonlocal n
            return lib.fun_si(n, s.encode("utf-8"))

        setattr(module, fun_name, tmp)


def load_nim_lib(lib_name, python_name):
    lib_name2 = lib_name
    if not (lib_name.endswith(".dll") or lib_name.endswith(".so")):
        if os.name == "nt":
            lib_name2 = lib_name + ".dll"
        else:
            lib_name2 = lib_name + ".so"

    lib = ffi.dlopen(lib_name2)

    ffi.cdef("""
        char* library_init();
        void library_deinit();
        int fun_vi(int fun_id);
        char* fun_ss(int fun_id, char* parm);
        int fun_si(int fun_id, char* arg); 
        int fun_ii(int fun_id, int arg); 
        double fun_ff(int fun_id, double arg); 
        char* fun_jj(int fun_id, char* arg);
    """)
    module = Module()
    setattr(sys.modules[__name__], python_name, module)

    x = lib.library_init()
    z = ffi.string(x)
    config = json.loads(z)
    for item in config:
        name, t = item["name"].split(":")
        n = item["n"]
        def_module_function(module, lib, name, t, n)
    return lib
