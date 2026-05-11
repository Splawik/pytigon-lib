"""CFFI-based loader for Nim-compiled shared libraries.

Provides dynamic function binding from Nim-generated .so/.dll files
into Python module attributes.
"""

import json
from cffi import FFI
import sys
import os

ffi = FFI()


class Module:
    """Namespae placeholder to which dynamically defined functions are attached."""

    pass


def def_module_function(module, lib, fun_name, t, n):
    """Define a Python wrapper function for a Nim library function.

    The type signature *t* determines the marshalling:
    - ``jj``: JSON to JSON (kwargs dict <-> JSON string)
    - ``ii``: int to int
    - ``ff``: float to float
    - ``vi``: void to int
    - ``ss``: string to string (also creates ``fun_name_str`` returning bytes)
    - ``si``: string to int

    Args:
        module: The Python module/namespace to attach the function to.
        lib: The CFFI library handle.
        fun_name: Name for the Python function.
        t: Two-character type signature.
        n: Numeric function ID passed to the Nim dispatcher.

    Raises:
        ValueError: If the type signature is not recognized.
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
        # String -> string variant (returns decoded UTF-8)
        def tmp(s):
            ret = lib.fun_ss(n, s.encode("utf-8"))
            ret_str = ffi.string(ret)
            return ret_str.decode("utf-8")

        setattr(module, fun_name + "_str", tmp)

        # String -> bytes variant (returns raw bytes)
        def tmp(s):
            ret = lib.fun_ss(n, s)
            ret_str = ffi.string(ret)
            return ret_str

    elif t == "si":

        def tmp(s):
            return lib.fun_si(n, s.encode("utf-8"))

    else:
        raise ValueError(f"Unsupported type signature: {t!r}")

    setattr(module, fun_name, tmp)


def load_nim_lib(lib_name, python_name):
    """Load a Nim shared library and expose its functions as a Python module.

    The library must export standard dispatcher functions (fun_vi, fun_ss, etc.)
    and a ``library_init()`` that returns a JSON configuration describing
    the available functions.

    Args:
        lib_name: Base name of the shared library (without extension).
        python_name: Name for the dynamically created Python module.

    Returns:
        The CFFI library handle.

    Raises:
        OSError: If the shared library cannot be loaded.
        RuntimeError: If initialization or function definition fails.
    """
    # Append platform-appropriate extension if not already present
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
            raise RuntimeError(f"Failed to define function {item['name']!r}: {e}")

    return lib
