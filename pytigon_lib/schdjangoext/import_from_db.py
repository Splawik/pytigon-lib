import sys
import types
import os
import importlib.abc
from importlib.machinery import ModuleSpec
from django.conf import settings


class DBModuleLoader(importlib.abc.SourceLoader):
    def get_filename(self, path):
        return path.replace(".", os.sep) + ".dbpy"

    def get_data(self, path):
        x = path.split(".")
        if len(x) == 5:
            module_name = x[1] + ".models"
            tmp = __import__(module_name, fromlist=[x[2]])
            model = getattr(tmp, x[2])
            if hasattr(model, "import"):
                return model.import_from_source(x[3], x[4])
        return ""

    def create_module(self, spec):
        mod = types.ModuleType(spec.name)
        mod.__file__ = self.get_filename("dbmodule")
        mod.__package__ = "dbmodule"
        sys.modules[mod.__name__] = mod
        return mod


class DBPackageLoader(importlib.abc.Loader):
    @classmethod
    def exec_module(klass, module):
        load_path = module.__spec__.origin
        init_file_name = "__init__.dbpy"
        if load_path.endswith(init_file_name):
            module.__path__ = [load_path[: -len(init_file_name) - 1]]


class DBFinder(importlib.abc.MetaPathFinder):
    @classmethod
    def find_spec(klass, full_name, paths=None, target=None):
        if full_name.startswith("dbmodule"):
            x = full_name.split(".")
            if len(x) < 5:
                full_path = os.path.join(full_name, "__init__.dbpy")
                return ModuleSpec(full_name, DBPackageLoader(), origin=full_path)
            else:
                full_path = full_name.replace(".", os.sep) + ".dbpy"
                return ModuleSpec(full_name, DBModuleLoader(), origin=full_path)
        else:
            return None


sys.meta_path.insert(0, DBFinder())


class ModuleStruct:
    def __init__(self, globals_dict, locals_dict):
        self.__dict__.update(globals_dict)
        self.__dict__.update(locals_dict)


def run_code_from_db_field(
    src_name, obj, field_name, function_name, locals_dict, globals_dict, **argv
):
    field = getattr(obj, field_name)
    if field:
        gen_path = os.path.join(settings.DATA_PATH, settings.PRJ_NAME, "syslib")
        gen_name = src_name.format(**(locals_dict | globals_dict))

        src_file_path = os.path.join(gen_path, gen_name)

        if os.path.exists(src_file_path):
            field_utf = field.encode("utf-8")
            file_stats = os.stat(src_file_path)
            if file_stats.st_size != len(field_utf):
                with open(src_file_path, "wb") as f:
                    f.write(field_utf)
        else:
            os.makedirs(gen_path, exist_ok=True)
            with open(src_file_path, "wb") as f:
                f.write(field.encode("utf-8"))

        x = __import__(gen_name.replace(".py", ""))
        fun = getattr(x, function_name)
        return fun(**argv)

        # exec(field, globals(), locals())
        # return locals()["function_name"](**argv)
    else:
        return None
