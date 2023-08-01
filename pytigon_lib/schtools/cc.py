#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

# Pytigon - wxpython and django application framework

# author: "Slawomir Cholaj (slawomir.cholaj@gmail.com)"
# copyright: "Copyright (C) ????/2012 Slawomir Cholaj"
# license: "LGPL 3.0"t
# version: "0.1a"


import os
import sys
import platform

from pytigon_lib.schtools.platform_info import platform_name

if platform_name() != "Emscripten":
    import httpx

import tarfile
import zipfile
import io
import sys
import importlib
from shutil import copyfile
from pathlib import Path
from pytigon_lib.schtools.process import run, py_run
from pytigon_lib.schtools.main_paths import get_main_paths, get_python_version


COMPILER_INITIALIZED = False


def init_compiler():
    global COMPILER_INITIALIZED
    if not COMPILER_INITIALIZED:
        import ziglang

        os.environ["PY_ZIG"] = os.path.join(ziglang.__path__[0], "zig")
        COMPILER_INITIALIZED = True


def compile(build_zig, output_file_name=None):
    cmd = [
        sys.executable,
        "-m",
        "ziglang",
        "build",
        "--prefix-exe-dir",
        "../../",
        "--prefix-lib-dir",
        "../../",
    ]
    base_path = os.path.dirname(build_zig)
    cwd = os.getcwd()
    os.chdir(base_path)
    (ret_code, output, err) = run(cmd)
    os.chdir(cwd)
    return (ret_code, output, err)


def make(data_path, files_path, prj_name=None):
    if platform_name() == "Emscripten":
        return None, None, None
    ret_output = []
    ret_errors = []
    ret = 0

    p = Path(files_path)

    fl = p.glob("**/build.zig")
    for pos in fl:
        init_compiler()
        c_filename = p.joinpath(pos).as_posix()
        if os.path.exists(c_filename):
            (ret_code, output, err) = compile(c_filename)
            if ret_code:
                ret = ret_code
            if output:
                for pos2 in output:
                    ret_output.append(pos2)
            if err:
                for pos2 in err:
                    ret_errors.append(pos2)

    fl = p.glob("**/build.py")
    for pos in fl:
        init_compiler()
        c_filename = p.joinpath(pos).as_posix()
        if os.path.exists(c_filename):
            if prj_name:
                cmd = [sys.executable, "build.py"]
                base_path = os.path.dirname(pos)
                cwd = os.getcwd()
                os.chdir(base_path)
                (ret_code, output, err) = run(cmd)
                os.chdir(cwd)

                if ret_code:
                    ret = ret_code
                if output:
                    for pos2 in output:
                        ret_output.append(pos2)
                if err:
                    for pos2 in err:
                        ret_errors.append(pos2)

    fl = p.glob("**/setup.py")
    for pos in fl:
        init_compiler()
        c_filename = p.joinpath(pos).as_posix()
        if os.path.exists(c_filename):
            if prj_name:
                cmd = [
                    sys.executable,
                    "-m",
                    "pytigon.ptig",
                    "pip_%s" % prj_name,
                    "install",
                    "-e",
                    c_filename,
                ]
                base_path = os.path.dirname(pos)
                cwd = os.getcwd()
                os.chdir(base_path)
                (ret_code, output, err) = run(cmd)
                os.chdir(cwd)

                if ret_code:
                    ret = ret_code
                if output:
                    for pos2 in output:
                        ret_output.append(pos2)
                if err:
                    for pos2 in err:
                        ret_errors.append(pos2)

    return ret, ret_output, ret_errors


def import_plugin(plugin_name, prj_name=None):
    cfg = get_main_paths()
    pytigon_cfg = [cfg["PYTIGON_PATH"], "appdata", "plugins"]
    data_path = cfg["DATA_PATH"]
    data_cfg = [data_path, "plugins"]
    prj_cfg = [cfg["PRJ_PATH"], prj_name, "applib"]
    prj_cfg_alt = [cfg["PRJ_PATH_ALT"], prj_name, "applib"]

    if prj_name:
        folders = [prj_cfg, prj_cfg_alt]
    else:
        folders = [pytigon_cfg, data_cfg]

    path = None
    for folder in folders:
        plugins_path = os.path.join(folder[0], *folder[1:])
        if prj_name:
            plugin_path = os.path.join(plugins_path, *plugin_name.split(".")[:-1])
        else:
            plugin_path = os.path.join(plugins_path, *plugin_name.split("."))
        if os.path.exists(plugin_path):
            path = plugins_path
            path2 = plugin_path
            break

    if not path:
        return None

    try:
        m = importlib.import_module(plugin_name, package=None)
        return m
    except:
        make(data_path, path2, prj_name)
        try:
            m = importlib.import_module(plugin_name, package=None)
            return m
        except:
            pass
    return None
