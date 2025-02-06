def sch_import(name):
    """
    Dynamically import a module by its name.

    Args:
        name (str): The full module name to import (e.g., 'package.module').

    Returns:
        module: The imported module.

    Raises:
        ImportError: If the module or any of its components cannot be imported.
    """
    try:
        mod = __import__(name)
        components = name.split(".")
        for comp in components[1:]:
            mod = getattr(mod, comp)
        return mod
    except (ImportError, AttributeError) as e:
        raise ImportError(f"Failed to import module '{name}': {e}")
