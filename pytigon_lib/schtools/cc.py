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


def check_compiler(base_path):
    if platform.system() == "Windows":
        tcc_dir = os.path.join(base_path, "ext_prg", "tcc")
        compiler = os.path.join(tcc_dir, "tcc.exe")
        return os.path.exists(compiler)
    else:
        return True


def extract_tar_folder(tf, folder, extract_to):
    os.makedirs(extract_to)

    def _members():
        l = len(folder)
        for member in tf.getmembers():
            if member.path.startswith(folder):
                member.path = member.path[l:]
                yield member

    tf.extractall(path=extract_to, members=_members())


def install_tcc(path):
    prg_path = os.path.abspath(os.path.join(path, ".."))

    if not os.path.exists(path):
        if not os.path.exists(prg_path):
            os.makedirs(prg_path)

        if platform.system() == "Windows":
            if sys.maxsize > 2 ** 32:
                url = "http://download.savannah.gnu.org/releases/tinycc/tcc-0.9.27-win64-bin.zip"
            else:
                url = "http://download.savannah.gnu.org/releases/tinycc/tcc-0.9.27-win32-bin.zip"
            r = httpx.get(url, allow_redirects=True)
            with zipfile.ZipFile(io.BytesIO(r.content)) as zfile:
                zfile.extractall(prg_path)
        else:
            url = "http://download.savannah.gnu.org/releases/tinycc/tcc-0.9.27.tar.bz2"
            r = httpx.get(url, allow_redirects=True)
            with tarfile.open(fileobj=io.BytesIO(r.content), mode="r:bz2") as tar:
                tar.extractall(prg_path)
            os.rename(os.path.join(prg_path, "tcc-0.9.27"), path)
            temp = os.getcwd()
            os.chdir(path)
            f = os.popen("./configure --disable-static")
            print(f.read())
            f = os.popen("make")
            print(f.read())
            os.chdir(temp)
    h_path = os.path.join(path, "include", "python")
    if not os.path.exists(h_path):
        info = sys.version_info
        url2 = f"https://www.python.org/ftp/python/{info.major}.{info.minor}.{info.micro}/Python-{info.major}.{info.minor}.{info.micro}.tgz"
        r = httpx.get(url2, allow_redirects=True)
        with tarfile.open(fileobj=io.BytesIO(r.content), mode="r:gz") as tar:
            extract_tar_folder(
                tar, f"Python-{info.major}.{info.minor}.{info.micro}/Include/", h_path
            )

    if platform.system() == "Windows":
        pytigon_path = os.path.abspath(os.path.dirname(__file__))
        src = os.path.join(pytigon_path, "tinyc", "python37.def")
        dst = os.path.join(path, "lib", "python37.def")
        copyfile(src, dst)
        src = os.path.join(pytigon_path, "tinyc", "pyconfig.h")
        dst = os.path.join(path, "include", "python", "pyconfig.h")
        copyfile(src, dst)


def compile(base_path, input_file_name, output_file_name=None, pyd=True):
    if platform.system() == "Windows":
        tcc_dir = os.path.join(base_path, "ext_prg", "tcc")
        h_dir = os.path.join(tcc_dir, "include", "python")
        if platform_name() != "Emscripten":
            if not os.path.exists(h_dir):
                install_tcc(tcc_dir)
        include1 = os.path.join(tcc_dir, "include")
        include2 = os.path.join(tcc_dir, "include", "python")
        include3 = os.path.join(tcc_dir, "include", "winapi")
        includes = [include1, include2, include3]
        tmp = os.getcwd()
        os.chdir(tcc_dir)
    else:
        # include1 = os.path.join(tcc_dir, "include")
        include1 = "/usr/include"
        include2 = "/usr/include/python%s" % get_python_version(segments=2)
        includes = [include1, include2]

    if output_file_name:
        ofn = output_file_name
    else:
        if platform.system() == "Windows":
            if pyd:
                ofn = input_file_name.replace(".c", "") + ".pyd"
            else:
                ofn = input_file_name.replace(".c", "") + ".dll"
            compiler = ".\\tcc.exe"
        else:
            ofn = input_file_name.replace(".c", "") + ".so"
            compiler = "tcc"

    if platform.system() == "Windows":
        cmd = [
            compiler,
            input_file_name,
            "-o",
            ofn,
            "-shared",
            "-L" + tcc_dir,
            "-B" + tcc_dir,
            "-ltcc",
            "-lpython%s" % (get_python_version(segments=2).replace(".", "")),
        ]
    else:
        # cmd = [compiler, input_file_name, '-o', ofn, '-shared', "-L" + tcc_dir, "-B"+tcc_dir , "-ltcc", "-lpython39"]
        cmd = [compiler, input_file_name, "-o", ofn, "-shared", "-fPIC"]

    for include in includes:
        cmd.append("-I" + include + "")

    print(cmd)

    (ret_code, output, err) = run(cmd)

    if platform.system() == "Windows":
        os.chdir(tmp)

    return (ret_code, output, err)


def make(data_path, files_path):
    if platform_name() == "Emscripten":
        return None, None, None
    ret_output = []
    ret_errors = []
    ret = 0

    p = Path(files_path)
    fl = p.glob("**/*.pyx")
    for pos in fl:
        pyx_filename = p.joinpath(pos).as_posix()
        c_filename = pyx_filename.replace(".pyx", ".c")
        (ret_code, output, err) = py_run(["-m", "cython", "-3", pyx_filename])
        if ret_code:
            ret = ret_code
        if output:
            for pos2 in output:
                ret_output.append(pos2)
        if err:
            for pos2 in err:
                ret_errors.append(pos2)
        if os.path.exists(c_filename):
            (ret_code, output, err) = compile(data_path, c_filename, pyd=True)
            if ret_code:
                ret = ret_code
            os.unlink(c_filename)
            if output:
                for pos2 in output:
                    ret_output.append(pos2)
            if err:
                for pos2 in err:
                    ret_errors.append(pos2)
    fl = p.glob("**/*.c")
    for pos in fl:
        c_filename = p.joinpath(pos).as_posix()
        if os.path.exists(c_filename):
            (ret_code, output, err) = compile(data_path, c_filename, pyd=False)
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
        make(data_path, path2)
        try:
            m = importlib.import_module(plugin_name, package=None)
            return m
        except:
            pass
    return None
