import tempfile
import os
from os import environ
import sys
from typing import Dict, Optional
import pytest

PRJ_NAME = ""


def if_not_in_env(name: str, default_value: str) -> str:
    """Return the environment variable value if it exists, otherwise return the default value."""
    return environ.get(f"PYTIGON_{name}", default_value)


def get_main_paths(prj_name: Optional[str] = None) -> Dict[str, str]:
    """Retrieve and return the main paths based on the project name and environment settings."""
    global PRJ_NAME

    if prj_name:
        PRJ_NAME = prj_name

    ret: Dict[str, str] = {}
    platform_type = "standard"
    ret["TEMP_PATH"] = tempfile.gettempdir()

    try:
        import pytigon.schserw as pytigon_schserw

        serw_path = os.path.dirname(os.path.abspath(pytigon_schserw.__file__))
        pytigon_path = os.path.abspath(os.path.join(serw_path, ".."))
    except ImportError:
        serw_path = None
        pytigon_path = None

    root_path = environ.get(
        "PYTIGON_ROOT_PATH",
        os.path.abspath(os.path.join(serw_path, "..")) if serw_path else None,
    )
    home_path = environ.get("SNAP_REAL_HOME", os.path.expanduser("~"))
    cwd = environ.get("START_PATH", os.path.abspath(os.getcwd()))

    ret["SERW_PATH"] = if_not_in_env("SERW_PATH", serw_path)
    ret["ROOT_PATH"] = root_path
    ret["PYTIGON_PATH"] = if_not_in_env("PYTIGON_PATH", pytigon_path)

    if "www-data" in cwd:
        platform_type = "webserver"
        home_path = "/home/www-data/"
    elif not pytigon_schserw:
        platform_type = "pytigon-lib"

    ret["PLATFORM_TYPE"] = platform_type

    if "DATA_PATH" in environ:
        data_path = if_not_in_env("DATA_PATH", environ["DATA_PATH"])
        ret["DATA_PATH"] = data_path
        ret["LOG_PATH"] = if_not_in_env(
            "LOG_PATH", "/var/log" if platform_type == "webserver" else data_path
        )
        ret["PRJ_PATH"] = if_not_in_env("PRJ_PATH", os.path.join(data_path, "prj"))
        ret["PRJ_PATH_ALT"] = if_not_in_env(
            "PRJ_PATH_ALT", os.path.join(root_path, "prj")
        )
    else:
        if platform_type == "android":
            p1 = os.path.join(environ.get("SECONDARY_STORAGE", ""), "pytigon_data")
            p2 = os.path.join(environ.get("EXTERNAL_STORAGE", ""), "pytigon_data")
            data_path = p2 if os.path.exists(p2) else p1
            ret["DATA_PATH"] = ret["LOG_PATH"] = if_not_in_env("DATA_PATH", data_path)
            ret["PRJ_PATH"] = if_not_in_env(
                "PRJ_PATH",
                os.path.abspath(os.path.join(data_path, "..", "pytigon", "prj")),
            )
            ret["PRJ_PATH_ALT"] = if_not_in_env(
                "PRJ_PATH_ALT", os.path.join(root_path, "prj")
            )
        else:
            data_path = if_not_in_env(
                "DATA_PATH", os.path.join(home_path, "pytigon_data")
            )
            ret["DATA_PATH"] = data_path
            ret["LOG_PATH"] = if_not_in_env("LOG_PATH", data_path)
            ret["PRJ_PATH"] = if_not_in_env("PRJ_PATH", os.path.join(data_path, "prj"))
            ret["PRJ_PATH_ALT"] = if_not_in_env(
                "PRJ_PATH_ALT", os.path.join(root_path, "prj")
            )

    static_path = environ.get(
        "STATIC_PATH", os.path.join(pytigon_path, "static") if pytigon_path else None
    )
    if platform_type == "webserver":
        ret["STATIC_PATH"] = if_not_in_env(
            "STATIC_PATH",
            (
                os.path.join(data_path, "static", PRJ_NAME)
                if PRJ_NAME
                else os.path.join(data_path, "static")
            ),
        )
        ret["STATICFILES_DIRS"] = [os.path.join(pytigon_path, "static")]
    else:
        ret["STATIC_PATH"] = if_not_in_env("STATIC_PATH", static_path)
        ret["STATICFILES_DIRS"] = []

    if PRJ_NAME:
        ret["MEDIA_PATH"] = if_not_in_env(
            "MEDIA_PATH", os.path.join(ret["DATA_PATH"], PRJ_NAME, "media")
        )
        ret["MEDIA_PATH_PROTECTED"] = if_not_in_env(
            "MEDIA_PATH_PROTECTED",
            os.path.join(ret["DATA_PATH"], PRJ_NAME, "protected_media"),
        )
        ret["UPLOAD_PATH"] = if_not_in_env(
            "UPLOAD_PATH", os.path.join(ret["MEDIA_PATH"], "upload")
        )
        ret["UPLOAD_PATH_PROTECTED"] = if_not_in_env(
            "UPLOAD_PROTECTED_PATH", os.path.join(ret["MEDIA_PATH"], "protected_upload")
        )

        if not os.path.exists(
            os.path.join(ret["PRJ_PATH"], PRJ_NAME, "settings_app.py")
        ):
            if os.path.exists(
                os.path.join(ret["PRJ_PATH_ALT"], PRJ_NAME, "settings_app.py")
            ):
                ret["PRJ_PATH"], ret["PRJ_PATH_ALT"] = (
                    ret["PRJ_PATH_ALT"],
                    ret["PRJ_PATH"],
                )
            else:
                ret["PRJ_PATH"] = if_not_in_env(
                    "PRJ_PATH", os.path.abspath(os.path.join(pytigon_path, ".."))
                )

        prj_static_path = os.path.join(ret["PRJ_PATH"], PRJ_NAME, "static")
        if (
            prj_static_path not in ret["STATICFILES_DIRS"]
            and prj_static_path != ret["STATIC_PATH"]
        ):
            ret["STATICFILES_DIRS"].append(prj_static_path)

    return ret


def get_prj_name() -> str:
    """Return the current project name."""
    global PRJ_NAME
    return PRJ_NAME


def get_python_version(segments: int = 3) -> str:
    """Return the Python version with the specified number of segments."""
    version_parts = sys.version.split(" ")[0].split(".")
    return ".".join(version_parts[:segments])
