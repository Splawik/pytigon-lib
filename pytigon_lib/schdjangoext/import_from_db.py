import sys
import types
import os
import datetime
import time
import importlib.abc
from importlib.machinery import ModuleSpec
from django.conf import settings
import importlib

CACHE = {}


def _get_setting(name, default=None):
    """Safely retrieve a Django setting with a fallback default.

    Args:
        name (str): The setting name.
        default: Fallback value if the setting is not defined.

    Returns:
        The setting value or the default.
    """
    return getattr(settings, name, default)


def in_cache(key):
    """Check if a key is in the cache and not expired.

    Args:
        key (str): Cache key to look up.

    Returns:
        bool: True if the key exists and has not expired.
    """
    global CACHE
    if key in CACHE:
        cache_timeout = _get_setting("EXECUTE_DB_CODE_CACHE_TIMEOUT", 0)
        if not cache_timeout:
            return True
        cache_time = CACHE[key][1]
        time_diff = (datetime.datetime.now() - cache_time).total_seconds()
        return time_diff < cache_timeout
    return False


def add_to_cache(key, value):
    """Add a key-value pair to the cache with the current timestamp.

    Args:
        key (str): Cache key.
        value: Value to store.
    """
    global CACHE
    CACHE[key] = (value, datetime.datetime.now())


def get_from_cache(key):
    """Retrieve a value from the cache by key.

    Args:
        key (str): Cache key.

    Returns:
        The cached value, or None if the key is missing.
    """
    global CACHE
    return CACHE.get(key, (None,))[0]


def func_from_func_content(func_name, content, argv):
    """Generate a function definition string from function content and arguments."""
    func_def = f"def {func_name}("
    if argv:
        func_def += ",".join(argv)
    func_def += "):\n"
    func_def += "\n".join(f"    {line}" for line in content.split("\n"))
    return func_def


class DBModuleLoader(importlib.abc.SourceLoader):
    """Loader for modules stored in the database."""

    def get_filename(self, path):
        """Get the filename for the given module path."""
        return path.replace(".", os.sep) + ".dbpy"

    def get_data(self, path):
        """Retrieve the module data from the database."""
        parts = path.split(".")
        if len(parts) == 5:
            module_name = f"{parts[1]}.models"
            tmp = __import__(module_name, fromlist=[parts[2]])
            model = getattr(tmp, parts[2])
            if hasattr(model, "import"):
                return model.import_from_source(parts[3], parts[4])
        return ""

    def create_module(self, spec):
        """Create a new module object."""
        mod = types.ModuleType(spec.name)
        mod.__file__ = self.get_filename("dbmodule")
        mod.__package__ = "dbmodule"
        sys.modules[mod.__name__] = mod
        return mod


class DBPackageLoader(importlib.abc.Loader):
    """Loader for packages stored in the database."""

    @classmethod
    def exec_module(cls, module):
        """Execute the module."""
        load_path = module.__spec__.origin
        init_file_name = "__init__.dbpy"
        if load_path.endswith(init_file_name):
            module.__path__ = [load_path[: -len(init_file_name) - 1]]


class DBFinder(importlib.abc.MetaPathFinder):
    """Finder for database modules and packages."""

    @classmethod
    def find_spec(cls, full_name, paths=None, target=None):
        """Find the module specification for the given full name."""
        if full_name.startswith("dbmodule"):
            parts = full_name.split(".")
            if len(parts) < 5:
                full_path = os.path.join(full_name, "__init__.dbpy")
                return ModuleSpec(full_name, DBPackageLoader(), origin=full_path)
            else:
                full_path = full_name.replace(".", os.sep) + ".dbpy"
                return ModuleSpec(full_name, DBModuleLoader(), origin=full_path)
        return None


sys.meta_path.insert(0, DBFinder())


class ModuleStruct:
    """Structure to hold module globals and locals."""

    def __init__(self, globals_dict, locals_dict):
        self.__dict__.update(globals_dict)
        self.__dict__.update(locals_dict)


def get_fun_from_db_field(
    src_name, base_object, field_name, function_name=None, argv=None
):
    """Retrieve a function from a database field.

    Supports multiple execution strategies controlled by
    ``settings.EXECUTE_DB_CODE``:

    - ``"import"``: Write to a file and import.
    - ``"import_and_cache"``: Write, import, and cache the result.
    - ``"exec_and_cache"``: Execute via ``exec()`` and cache.
    - Other / unset: Execute via ``exec()`` without caching.

    Args:
        src_name: Source identifier used for caching and file naming.
        base_object: Object that owns the field.
        field_name: Name of the field containing the source code.
        function_name: Optional name of the function to extract.
        argv: Optional list of argument names for wrapping bare code
              into a function.

    Returns:
        The callable function, or None if the field is empty.
    """
    execute_mode = _get_setting("EXECUTE_DB_CODE", "exec")

    if not function_name:
        function_name = field_name

    if execute_mode in ("import_and_cache", "exec_and_cache") and in_cache(src_name):
        return get_from_cache(src_name)

    f = getattr(base_object, field_name)
    if not f:
        return None

    # Wrap bare code (without 'def') into a callable function
    if "def " not in f and "\ndef " not in f:
        field = func_from_func_content(function_name, f, argv)
    else:
        field = f

    if execute_mode in ("import", "import_and_cache"):
        gen_path = os.path.join(
            _get_setting("DATA_PATH", ""),
            _get_setting("PRJ_NAME", "default"),
            "syslib",
        )
        src_file_path = os.path.join(gen_path, src_name)
        file_changed = False

        if os.path.exists(src_file_path):
            field_utf = field.encode("utf-8")
            file_stats = os.stat(src_file_path)
            if file_stats.st_size != len(field_utf):
                with open(src_file_path, "wb") as fh:
                    fh.write(field_utf)
                file_changed = True
                time.sleep(0.01)
        else:
            os.makedirs(gen_path, exist_ok=True)
            with open(src_file_path, "wb") as fh:
                fh.write(field.encode("utf-8"))
            file_changed = True
            time.sleep(0.1)

        # Bypass the import cache only when the file actually changed
        imp_name = src_name.replace(".py", "")
        if file_changed and imp_name in sys.modules:
            del sys.modules[imp_name]
        x = __import__(imp_name)
        fun = getattr(x, function_name)
        if execute_mode == "import_and_cache":
            add_to_cache(src_name, fun)
        return fun

    elif execute_mode == "exec_and_cache":
        local_vars = {}
        exec(field, globals(), local_vars)
        fun = local_vars.get(function_name)
        if fun is not None:
            add_to_cache(src_name, fun)
        return fun

    else:
        local_vars = {}
        exec(field, globals(), local_vars)
        return local_vars.get(function_name)


def run_code_from_db_field(
    src_name, base_object, field_name, function_name=None, **argv
):
    """Run code from a database field.

    Retrieves a function stored in a database field and calls it
    with the given keyword arguments.

    Args:
        src_name: Source identifier for caching.
        base_object: Object that owns the field.
        field_name: Name of the field containing the source code.
        function_name: Optional name of the function to call.
        **argv: Keyword arguments forwarded to the function.

    Returns:
        The return value of the function, or None if not found.
    """
    fun = get_fun_from_db_field(src_name, base_object, field_name, function_name, argv)
    if fun is not None:
        return fun(**argv)
    return None
