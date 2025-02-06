import json
from cffi import FFI
import sys
import os

ffi = FFI()


class Module:
    """A placeholder class for dynamically adding module functions."""

    pass


def def_module_function(module, lib, fun_name, t, n):
    """
    Dynamically defines a function in the module based on the type signature.

    Args:
        module: The module to which the function will be added.
        lib: The shared library containing the function.
        fun_name: The name of the function to be added.
        t: The type signature of the function.
        n: The function ID.
    """
    if t == "jj":

        def tmp(**kwargs):
            ret = lib.fun_jj(n, json.dumps(kwargs).encode("utf-8"))
            ret_str = ffi.string(ret)
            return json.loads(ret_str)

    elif t == "ii":

        def tmp(arg):
            return lib.fun_ii(n, arg)

    elif t == "ff":

        def tmp(arg):
            return lib.fun_ff(n, arg)

    elif t == "vi":

        def tmp():
            return lib.fun_vi(n)

    elif t == "ss":

        def tmp(s):
            ret = lib.fun_ss(n, s.encode("utf-8"))
            ret_str = ffi.string(ret)
            return ret_str.decode("utf-8")

        setattr(module, fun_name + "_str", tmp)

        def tmp(s):
            ret = lib.fun_ss(n, s)
            ret_str = ffi.string(ret)
            return ret_str

    elif t == "si":

        def tmp(s):
            return lib.fun_si(n, s.encode("utf-8"))

    else:
        raise ValueError(f"Unsupported type signature: {t}")

    setattr(module, fun_name, tmp)


def load_nim_lib(lib_name, python_name):
    """
    Loads a Nim shared library and initializes the corresponding Python module.

    Args:
        lib_name: The base name of the shared library.
        python_name: The name of the Python module to be created.

    Returns:
        The loaded shared library.
    """
    lib_name2 = lib_name
    if not (lib_name.endswith(".dll") or lib_name.endswith(".so")):
        lib_name2 = lib_name + (".dll" if os.name == "nt" else ".so")

    try:
        lib = ffi.dlopen(lib_name2)
    except OSError as e:
        raise OSError(f"Failed to load library {lib_name2}: {e}")

    ffi.cdef(
        """
        char* library_init();
        void library_deinit();
        int fun_vi(int fun_id);
        char* fun_ss(int fun_id, char* parm);
        int fun_si(int fun_id, char* arg); 
        int fun_ii(int fun_id, int arg); 
        double fun_ff(int fun_id, double arg); 
        char* fun_jj(int fun_id, char* arg);
    """
    )

    module = Module()
    setattr(sys.modules[__name__], python_name, module)

    try:
        x = lib.library_init()
        z = ffi.string(x)
        config = json.loads(z)
    except Exception as e:
        raise RuntimeError(f"Failed to initialize library: {e}")

    for item in config:
        try:
            name, t = item["name"].split(":")
            n = item["n"]
            def_module_function(module, lib, name, t, n)
        except Exception as e:
            raise RuntimeError(f"Failed to define function {item['name']}: {e}")

    return lib
