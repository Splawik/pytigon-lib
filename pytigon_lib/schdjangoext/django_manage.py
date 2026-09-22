import logging
import os
import sys
import site
import importlib
import configparser
from django.core.management import execute_from_command_line

_logger = logging.getLogger(__name__)


def cmd(arg, from_main=False):
    """
    Execute a Django management command.

    Args:
        arg (str or list): The command to execute. If a string, it will be converted to a list.
        from_main (bool): If True, `arg` is treated as the full command line arguments.

    Raises:
        SystemExit: If the command execution fails.
    """
    try:
        if from_main:
            argv = arg
        else:
            argv = ["manage.py"] + ([arg] if isinstance(arg, str) else arg)

        from pytigon_lib.schtools.main_paths import get_main_paths

        config = configparser.ConfigParser()
        config.read("install.ini")
        prj_name = config.get("DEFAULT", "PRJ_NAME", fallback="")
        if prj_name:
            main_paths = get_main_paths(prj_name)
            data_path = main_paths["DATA_PATH"]
            os.environ["PYTHONUSERBASE"] = os.path.join(data_path, prj_name, "prjlib")
            importlib.reload(site)
            prjlib = site.getusersitepackages()
            sys.path.insert(0, prjlib)

        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings_app")
        execute_from_command_line(argv)
    except Exception as e:
        import traceback  #

        _logger.error("Error executing command: %s", e)
        traceback.print_exc()
        sys.exit(1)


def syncdb():
    """Synchronize the database."""
    cmd("syncdb")


def help():
    """Display help information."""
    cmd("help")


if __name__ == "__main__":
    cmd(sys.argv, from_main=True)
