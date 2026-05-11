def sch_import(name):
    """
    Dynamically import a module by its dotted name.

    Uses importlib.import_module for reliable Python 3 import semantics.
    When importing a submodule of a package, this ensures the top-level package
    is also available in sys.modules.

    Args:
        name (str): The full dotted module name to import (e.g., 'package.module').

    Returns:
        module: The imported module object.

    Raises:
        ImportError: If the module cannot be found or imported.
    """
    import importlib

    try:
        return importlib.import_module(name)
    except ImportError as e:
        raise ImportError(f"Failed to import module '{name}': {e}")
