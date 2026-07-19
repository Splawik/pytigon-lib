"""
Initialize system paths based on the project name and environment path.

This function sets up the necessary system paths for the project by:
1. Loading environment configurations if an environment path is provided.
2. Removing duplicate and relative paths from `sys.path`.
3. Adding platform-specific paths to `sys.path`.
4. Adding project-specific paths to `sys.path`.
5. Adding additional paths related to external libraries and plugins.


Raises:
    Exception: If there is an error during the initialization of paths, it logs the error
        message and raises the exception.

author: Sławomir Chołaj (slawomir.cholaj@gmail.com)
license: LGPL 3.0
"""

__version__ = "0.260719"

import importlib.util
import logging
import os
import sys
from pathlib import Path

from pytigon_lib.schtools.env import get_environ
from pytigon_lib.schtools.main_paths import get_main_paths

_logger = logging.getLogger(__name__)


def _add_sys_path(path, *, priority=False):
    """Add *path* to ``sys.path`` unless it is already present.

    Args:
        path: Absolute path to add.
        priority: If True, the path is inserted at the front of ``sys.path``
            (higher precedence); otherwise it is appended.
    """
    if path and path not in sys.path:
        if priority:
            sys.path.insert(0, path)
        else:
            sys.path.append(path)


def init_paths(prj_name=None, env_path=None):
    """Initialize system paths based on the project name and environment path.

    Args:
        prj_name (str, optional): The name of the project. Defaults to None.
        env_path (str, optional): Path to the environment configuration. Defaults to None.
    """
    try:
        if env_path:
            get_environ(env_path)

        cfg = get_main_paths(prj_name)

        # Remove duplicate and relative paths from sys.path
        sys.path = list(dict.fromkeys(pos for pos in sys.path if not pos.startswith(".")))

        from pytigon_lib.schtools.platform_info import platform_name

        base_path = os.path.dirname(os.path.abspath(__file__))
        pname = platform_name()

        pytigon_base_path = importlib.util.find_spec("pytigon")
        ext_lib_path = None
        if pytigon_base_path:
            ext_lib_path = os.path.abspath(os.path.join(Path(pytigon_base_path.origin).parent, "ext_lib"))

        # Platform-specific path adjustments
        if pname == "Android":
            bundled_path = os.path.abspath(os.path.join(base_path, "..", "_android"))
        else:
            if pname == "Windows":
                bundled_path = os.path.abspath(os.path.join(base_path, "..", "python", "lib", "site-packages"))
            else:
                bundled_path = os.path.abspath(
                    os.path.join(
                        base_path,
                        "..",
                        "python",
                        "lib",
                        f"python{sys.version_info[0]}.{sys.version_info[1]}/site-packages",
                    )
                )
        _add_sys_path(bundled_path, priority=True)
        _add_sys_path(ext_lib_path)

        # Add project-specific paths
        for path_key in ["SERW_PATH", "ROOT_PATH", "PRJ_PATH_ALT"]:
            _add_sys_path(cfg[path_key])

        # Add additional paths
        additional_paths = [
            os.path.join(cfg["ROOT_PATH"], "ext_lib"),
            os.path.join(cfg["ROOT_PATH"], "appdata", "plugins"),
            os.path.join(cfg["DATA_PATH"], "plugins"),
        ]
        if prj_name:
            additional_paths.extend(
                [
                    os.path.join(cfg["DATA_PATH"], prj_name, "syslib"),
                    os.path.join(cfg["PRJ_PATH"], prj_name, "prjlib"),
                    os.path.join(cfg["DATA_PATH"], prj_name, "prjlib"),
                ]
            )

        for path in additional_paths:
            if os.path.exists(path):
                _add_sys_path(path)

    except Exception as e:
        _logger.error("Error initializing paths: %s", e)
        raise
