# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY  ; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

# Pytigon - wxpython and django application framework

# author: "Slawomir Cholaj (slawomir.cholaj@gmail.com)"
# license: "LGPL 3.0"

__version__ = "0.250214"

"""
Initialize system paths based on the project name and environment path.

This function sets up the necessary system paths for the project by:
1. Loading environment configurations if an environment path is provided.
2. Removing duplicate and relative paths from `sys.path`.
3. Adding platform-specific paths to `sys.path`.
4. Adding project-specific paths to `sys.path`.
5. Adding additional paths related to external libraries and plugins.


Raises:
    Exception: If there is an error during the initialization of paths, it prints the error message and raises the exception.
"""

import sys
import os
from pytigon_lib.schtools.main_paths import get_main_paths
from pytigon_lib.schtools.env import get_environ


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
        sys.path = list(
            dict.fromkeys(pos for pos in sys.path if not pos.startswith("."))
        )

        from pytigon_lib.schtools.platform_info import platform_name

        base_path = os.path.dirname(os.path.abspath(__file__))
        pname = platform_name()

        # Platform-specific path adjustments
        if pname == "Android":
            p = os.path.abspath(os.path.join(base_path, "..", "_android"))
            p2 = os.path.abspath(os.path.join(base_path, "..", "ext_lib"))
            for path in [p, p2]:
                if path not in sys.path:
                    sys.path.insert(0, path) if path == p else sys.path.append(path)
        else:
            if pname == "Windows":
                p = os.path.abspath(
                    os.path.join(base_path, "..", "python", "lib", "site-packages")
                )
            else:
                p = os.path.abspath(
                    os.path.join(
                        base_path,
                        "..",
                        "python",
                        "lib",
                        f"python{sys.version_info[0]}.{sys.version_info[1]}/site-packages",
                    )
                )
            p2 = os.path.abspath(os.path.join(base_path, "..", "ext_lib"))
            for path in [p, p2]:
                if path not in sys.path:
                    sys.path.insert(0, path) if path == p else sys.path.append(path)

        # Add project-specific paths
        for path_key in ["SERW_PATH", "ROOT_PATH", "PRJ_PATH_ALT"]:
            if cfg[path_key] not in sys.path:
                sys.path.append(cfg[path_key])

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
            if path not in sys.path and os.path.exists(path):
                sys.path.append(path)

    except Exception as e:
        print(f"Error initializing paths: {e}")
        raise
