"""Determine filesystem paths for the Pytigon platform across environments.

The platform can run in several modes: client (AppImage/Emscripten),
development, web server, Android, or as a library (pytigon-lib).
"""

import os
import sys
import tempfile
from os import environ

from pytigon_lib.schtools.platform_info import platform_name

# Path layout by platform type:
#
#              Client(appimage,emscripten)  Client/DEV           Server
# ROOT_PATH    site-packages/pytigon        ./                    /home/www-data/www/pytigon
# SERW_PATH    site-packages/pytigon/schserw ./schserw            site-packages/pytigon/schserw
# DATA_PATH    ~/pytigon_data               ~/pytigon_data        /home/www-data/pytigon_data
# LOG_PATH     console                      console               /var/log
# TEMP_PATH    %TEMP%                       %TEMP%                %TEMP%
# PRJ_PATH     ~/pytigon_data/prj           ./prj                 /home/www-data/pytigon/prj
# PRJ_PATH_ALT site-packages/pytigon/prj    site-packages/pytigon/prj site-packages/pytigon/prj
# STATIC_PATH  site-packages/pytigon/static site-packages/pytigon/static site-packages/pytigon/static
#
#              Android                     pytigon-lib
# ROOT_PATH    site-packages/pytigon       None
# SERW_PATH    site-packages/pytigon/schserw None
# DATA_PATH    STORAGE/pytigon_data        ~/pytigon_data
# LOG_PATH     STORAGE/pytigon_data        ~/pytigon_data
# TEMP_PATH    %TEMP%                      %TEMP%
# PRJ_PATH     STORAGE/pytigon/prj         ~/pytigon_data/prj
# PRJ_PATH_ALT site-packages/pytigon/prj   None
# STATIC_PATH  site-packages/pytigon/static site-packages/pytigon/static

PRJ_NAME = ""


def if_not_in_env(name, value):
    """Return the environment variable PYTIGON_<name> if set, else value.

    Args:
        name: Suffix of the environment variable (e.g. 'DATA_PATH').
        value: Default value to return if the environment variable is not set.

    Returns:
        The environment variable value or the default.
    """
    env_key = "PYTIGON_" + name
    return environ.get(env_key, value)


def get_main_paths(prj_name=None):
    """Determine the main filesystem paths based on the runtime platform.

    Inspects environment variables, installed packages, and the current
    working directory to determine paths for data, logs, projects, static
    files, and media.

    Args:
        prj_name: Optional project name; sets the global PRJ_NAME if provided.

    Returns:
        A dictionary with keys like DATA_PATH, LOG_PATH, PRJ_PATH,
        STATIC_PATH, MEDIA_PATH, etc.
    """
    global PRJ_NAME

    if prj_name:
        PRJ_NAME = prj_name

    ret = {"TEMP_PATH": tempfile.gettempdir()}

    # Try to locate pytigon.schserw package
    try:
        import pytigon.schserw as pytigon_schserw
    except ImportError:
        pytigon_schserw = None

    pytigon_path = None
    if pytigon_schserw:
        serw_path = os.path.dirname(os.path.abspath(pytigon_schserw.__file__))
        pytigon_path = os.path.abspath(os.path.join(serw_path, ".."))
    else:
        serw_path = None

    if "PYTIGON_ROOT_PATH" in environ:
        root_path = environ["PYTIGON_ROOT_PATH"]
    else:
        root_path = os.path.abspath(os.path.join(serw_path, "..")) if serw_path else None

    home_path = environ.get("SNAP_REAL_HOME", os.path.expanduser("~"))

    ret["SERW_PATH"] = if_not_in_env("SERW_PATH", serw_path)
    ret["ROOT_PATH"] = root_path
    ret["PYTIGON_PATH"] = if_not_in_env("PYTIGON_PATH", pytigon_path)

    cwd = environ.get("START_PATH", os.path.abspath(os.getcwd()))

    # Determine platform type
    if platform_name() == "Android":
        platform_type = "android"
    elif not pytigon_schserw:
        platform_type = "pytigon-lib"
    elif "www-data" in cwd:
        platform_type = "webserver"
        home_path = "/home/www-data/"
    else:
        platform_type = "standard"

    ret["PLATFORM_TYPE"] = platform_type

    if "DATA_PATH" in environ:
        ret["DATA_PATH"] = data_path = if_not_in_env("DATA_PATH", environ["DATA_PATH"])
        if platform_type == "webserver":
            ret["LOG_PATH"] = if_not_in_env("LOG_PATH", "/var/log")
        elif platform_type == "pytigon-lib":
            ret["LOG_PATH"] = if_not_in_env("LOG_PATH", data_path)
        else:
            ret["LOG_PATH"] = if_not_in_env("LOG_PATH", data_path)
        ret["PRJ_PATH"] = if_not_in_env("PRJ_PATH", os.path.join(data_path, "prj"))
        ret["PRJ_PATH_ALT"] = if_not_in_env("PRJ_PATH_ALT", os.path.join(root_path, "prj") if root_path else "")
    else:
        if platform_type == "android":
            p1 = p2 = None
            if "SECONDARY_STORAGE" in environ:
                p1 = os.path.join(environ["SECONDARY_STORAGE"], "pytigon_data")
            if "EXTERNAL_STORAGE" in environ:
                p2 = os.path.join(environ["EXTERNAL_STORAGE"], "pytigon_data")
            if p1:
                data_path = p2 if (p2 and os.path.exists(p2)) else p1
            else:
                data_path = p2
            ret["DATA_PATH"] = ret["LOG_PATH"] = if_not_in_env("DATA_PATH", data_path)
            ret["PRJ_PATH"] = if_not_in_env(
                "PRJ_PATH",
                os.path.abspath(os.path.join(data_path, "..", "pytigon", "prj")),
            )
            ret["PRJ_PATH_ALT"] = if_not_in_env(
                "PRJ_PATH_ALT",
                os.path.join(root_path, "prj") if root_path else "",
            )

        elif platform_type == "webserver":
            ret["DATA_PATH"] = data_path = if_not_in_env("DATA_PATH", os.path.join(home_path, "pytigon_data"))
            ret["LOG_PATH"] = if_not_in_env("LOG_PATH", "/var/log")
            ret["PRJ_PATH"] = if_not_in_env("PRJ_PATH", os.path.join(data_path, "prj"))
            ret["PRJ_PATH_ALT"] = if_not_in_env(
                "PRJ_PATH_ALT",
                os.path.join(pytigon_path, "prj") if pytigon_path else "",
            )
        else:
            ret["DATA_PATH"] = data_path = if_not_in_env("DATA_PATH", os.path.join(home_path, "pytigon_data"))
            ret["LOG_PATH"] = if_not_in_env("LOG_PATH", data_path)
            ret["PRJ_PATH"] = if_not_in_env("PRJ_PATH", os.path.join(data_path, "prj"))
            ret["PRJ_PATH_ALT"] = if_not_in_env(
                "PRJ_PATH_ALT",
                os.path.join(root_path, "prj") if root_path else "",
            )
            if platform_name() == "Emscripten":
                ret["PRJ_PATH"] = if_not_in_env(
                    "PRJ_PATH",
                    os.path.abspath(os.path.join(pytigon_path, "..")),
                )
                ret["PRJ_PATH_ALT"] = if_not_in_env("PRJ_PATH_ALT", os.path.join(pytigon_path, "prj"))

    if "STATIC_PATH" in environ:
        static_path = environ["STATIC_PATH"]
    elif pytigon_path:
        static_path = os.path.join(pytigon_path, "static")
    else:
        static_path = None

    if platform_type == "webserver":
        if PRJ_NAME:
            ret["STATIC_PATH"] = if_not_in_env("STATIC_PATH", os.path.join(data_path, "static", PRJ_NAME))
        else:
            ret["STATIC_PATH"] = if_not_in_env("STATIC_PATH", os.path.join(data_path, "static"))
        ret["STATICFILES_DIRS"] = [
            os.path.join(pytigon_path, "static"),
        ]
    else:
        ret["STATIC_PATH"] = if_not_in_env("STATIC_PATH", static_path)
        if platform_name() == "Emscripten":
            ret["STATICFILES_DIRS"] = [
                os.path.join(pytigon_path, "static"),
            ]
        else:
            ret["STATICFILES_DIRS"] = []

    if PRJ_NAME:
        data_path_val = ret["DATA_PATH"]
        ret["MEDIA_PATH"] = if_not_in_env(
            "MEDIA_PATH",
            os.path.join(data_path_val, PRJ_NAME, "media"),
        )
        ret["MEDIA_PATH_PROTECTED"] = if_not_in_env(
            "MEDIA_PATH_PROTECTED",
            os.path.join(data_path_val, PRJ_NAME, "protected_media"),
        )
        ret["UPLOAD_PATH"] = if_not_in_env("UPLOAD_PATH", os.path.join(ret["MEDIA_PATH"], "upload"))
        ret["UPLOAD_PATH_PROTECTED"] = if_not_in_env(
            "UPLOAD_PROTECTED_PATH",
            os.path.join(ret["MEDIA_PATH"], "protected_upload"),
        )
        if not os.path.exists(os.path.join(ret["PRJ_PATH"], PRJ_NAME, "settings_app.py")):
            if os.path.exists(os.path.join(ret["PRJ_PATH_ALT"], PRJ_NAME, "settings_app.py")):
                tmp = ret["PRJ_PATH"]
                ret["PRJ_PATH"] = if_not_in_env("PRJ_PATH", ret["PRJ_PATH_ALT"])
                ret["PRJ_PATH_ALT"] = if_not_in_env("PRJ_PATH_ALT", tmp)
            elif pytigon_path:
                ret["PRJ_PATH"] = if_not_in_env("PRJ_PATH", os.path.abspath(os.path.join(pytigon_path, "..")))

        prj_static_path = os.path.join(ret["PRJ_PATH"], PRJ_NAME, "static")
        if prj_static_path not in ret["STATICFILES_DIRS"] and prj_static_path != ret["STATIC_PATH"]:
            ret["STATICFILES_DIRS"].append(prj_static_path)

    return ret


def get_prj_name():
    """Return the globally cached project name.

    Returns:
        The project name string set by get_main_paths().
    """
    global PRJ_NAME
    return PRJ_NAME


def get_python_version(segments=3):
    """Get the current Python version as a dotted string.

    Args:
        segments: Number of version segments to return (default 3, e.g. '3.10.12').

    Returns:
        Dotted version string.
    """
    x = sys.version.split(" ")[0].split(".")
    return ".".join(x[:segments])
