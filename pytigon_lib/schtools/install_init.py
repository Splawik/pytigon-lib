#! /usr/bin/python
# -*- coding: utf-8 -*-
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
# copyright: "Copyright (C) ????/2013 Slawomir Cholaj"
# license: "LGPL 3.0"
# version: "0.1a"

import os
import sys
import zipfile
import shutil
import configparser
import multiprocessing
from pytigon_lib.schfs import extractall
from pytigon_lib.schtools.process import py_manage
from pytigon_lib.schtools.process import py_run
from pytigon_lib.schtools.nim_integration import install_nim


def _mkdir(path, ext=None):
    if ext:
        p = os.path.join(path, ext)
    else:
        p = path
    if not os.path.exists(p):
        try:
            os.mkdir(p)
        except:
            pass


def upgrade_test(zip_path, out_path):
    if os.path.exists(zip_path):
        archive = zipfile.ZipFile(zip_path, "r")
        cfg_txt = archive.read("install.ini").decode("utf-8")
        cfg = configparser.ConfigParser()
        cfg.read_string(cfg_txt)
        t1 = cfg["DEFAULT"]["GEN_TIME"]
        ini2 = os.path.join(out_path, "install.ini")
        if os.path.exists(ini2):
            cfg2 = configparser.ConfigParser()
            cfg2.read(ini2)
            t2 = cfg2["DEFAULT"]["GEN_TIME"]
            if t2 < t1:
                return True
        else:
            return False
    return False


def pip_install(pip_str, prjlib, confirm=False, upgrade=False):
    packages = [x.strip() for x in pip_str.split(" ") if x]
    print("pip install: ", pip_str)
    exit_code, output_tab, err_tab = py_run(
        [
            "-m",
            "pip",
            "--disable-pip-version-check",
            "install",
            f"--target={prjlib}",
        ]
        + (
            [
                "--upgrade",
            ]
            if upgrade
            else []
        )
        + packages
    )
    success = False
    if output_tab:
        for pos in output_tab:
            if pos:
                print("pip info: ", pos)
            if "Successfully installed" in pos:
                success = True
    if err_tab:
        for pos in err_tab:
            if pos:
                print("pip error: ", pos)

    if success and confirm:
        return True
    else:
        return False


def build_all(path):
    ret = True
    for root, dirs, files in os.walk(path):
        for name in files:
            if name.endswith("_build.py"):
                p = os.path.join(root, name)
                with open(p, "rt") as f:
                    buf = f.read()
                    exec(buf)
                    if "build" in locals():
                        x = locals()["build"](path=p.replace("_build.py", ".nim"))
                        if not x:
                            ret = False
    return ret


def upgrade_local_libs():
    from django.conf import settings

    prjlib = os.path.join(settings.DATA_PATH, settings.PRJ_NAME, "prjlib")
    config_file = os.path.join(settings.PRJ_PATH, settings.PRJ_NAME, "install.ini")
    if os.path.exists(config_file):
        config = configparser.ConfigParser()
        config.read(config_file)
        if "DEFAULT" in config:
            pip_str = config["DEFAULT"].get("PIP", "")
            if pip_str:
                pip_install(pip_str, prjlib, confirm=True, upgrade=True)


SYS_COMMANDS = {
    "makeallmigrations",
    "migrate",
    "createautouser",
    "import_projects",
}


def init(prj, root_path, data_path, prj_path, static_app_path, paths=None):
    if prj == "_schall":
        return

    l = multiprocessing.Lock()
    l.acquire()

    _root_path = os.path.normpath(root_path)
    _data_path = os.path.normpath(data_path)
    _prj_path = os.path.normpath(prj_path)
    _static_app_path = os.path.normpath(static_app_path)
    # _base_compiler_path = os.path.join(_data_path, "ext_prg")
    # is_prj_path = True if os.path.exists(_prj_path) else False
    is_data_path = (
        True if os.path.exists(os.path.join(_data_path, "install.ini")) else False
    )
    is_dev = prj in ("schdevtools", "schmanage", "_schsetup")
    is_static_path = True if os.path.exists(_static_app_path) else False
    upgrade = False

    if is_data_path and is_dev:
        if upgrade_test(
            os.path.join(os.path.join(_root_path, "install"), ".pytigon.zip"),
            _data_path,
        ):
            upgrade = True
            print("Upgrade data")

    if not is_data_path:
        zip_file2 = os.path.join(os.path.join(_root_path, "install"), ".pytigon.zip")
        if not os.path.exists(_data_path):
            os.makedirs(_data_path)
        if os.path.exists(zip_file2) and is_dev:
            extractall(zipfile.ZipFile(zip_file2), _data_path)
        if not os.path.exists(os.path.join(_data_path, "media")):
            media_path = os.path.join(os.path.join(_data_path, "media"))
            os.makedirs(media_path)
            os.makedirs(os.path.join(media_path, "filer_public"))
            os.makedirs(os.path.join(media_path, "filer_private"))
            os.makedirs(os.path.join(media_path, "filer_public_tumbnails"))
            os.makedirs(os.path.join(media_path, "filer_private_thumbnails"))
        if not os.path.exists(os.path.join(_data_path, "doc")):
            doc_path = os.path.join(os.path.join(_data_path, "doc"))
            os.makedirs(doc_path)

        if SYS_COMMANDS.intersection(sys.argv):
            prjs = []
        elif is_dev:
            prjs = [ff for ff in os.listdir(_prj_path) if not ff.startswith("_")]
        else:
            prjs = [
                prj,
            ]

        tmp = os.getcwd()
        for app in prjs:
            path = os.path.join(_prj_path, app)
            if os.path.isdir(path):
                db_path = os.path.join(os.path.join(_data_path, app), f"{app}.db")
                os.chdir(path)
                print("python: pytigon: init: ", path)
                if not os.path.exists(db_path):
                    print("python: pytigon: init: create:", db_path)
                    exit_code, output_tab, err_tab = py_manage(
                        ["makeallmigrations"], False
                    )
                    if err_tab:
                        print(err_tab)
                    exit_code, output_tab, err_tab = py_manage(["migrate"], False)
                    if err_tab:
                        print(err_tab)
                    exit_code, output_tab, err_tab = py_manage(
                        ["createautouser"], False
                    )
                    if err_tab:
                        print(err_tab)
                    if app == "schdevtools":
                        print("python: pytigon: import_projects!")
                        exit_code, output_tab, err_tab = py_manage(
                            ["import_projects"], False
                        )
                        print("python: pytigon: projects imported!")
                        if err_tab:
                            print(err_tab)
        # install_nim(_data_path)
        os.chdir(tmp)

    if upgrade:
        zip_file2 = os.path.join(os.path.join(_root_path, "install"), ".pytigon.zip")
        if not os.path.exists(_data_path):
            os.makedirs(_data_path)
        if os.path.exists(zip_file2):
            extractall(zipfile.ZipFile(zip_file2), _data_path, exclude=[r".*\.db"])

    if not is_static_path:
        p2 = os.path.join(os.path.join(_root_path, "static"), "app")
        if os.path.exists(p2):
            shutil.copytree(p2, _static_app_path)

    _paths = [
        "",
        "cache",
        "plugins_cache",
        "_schall",
        "schdevtools",
        "prj",
        "temp",
        "static",
        prj,
    ]
    for p in _paths:
        _mkdir(_data_path, p)
    if paths:
        for p in paths:
            _mkdir(p)

    prjlib = os.path.join(_data_path, prj, "prjlib")
    if not os.path.exists(prjlib) or not os.path.exists(
        os.path.join(prjlib, "install.txt")
    ):
        ok = True
        if not os.path.exists(prjlib):
            os.mkdir(prjlib)
        config_file = os.path.join(prj_path, prj, "install.ini")
        if os.path.exists(config_file):
            config = configparser.ConfigParser()
            config.read(config_file)
            if "DEFAULT" in config:
                pip_str = config["DEFAULT"].get("PIP", "")
                if pip_str:
                    x = pip_install(pip_str, prjlib, confirm=True)
                    if not x:
                        ok = False
        x = build_all(os.path.join(_prj_path, prj))
        if not x:
            ok = False
        if ok:
            with open(os.path.join(prjlib, "install.txt"), "wt") as f:
                f.write("OK")

    if os.path.exists(prjlib):
        if prjlib not in sys.path:
            sys.path.append(prjlib)
        # if test1 or test2 or test3:
        #    ret = make(_data_path, os.path.join(_prj_path, prj), prj)
        #    if ret:
        #        for pos in ret:
        #            print(pos)
    syslib = os.path.join(_data_path, prj, "syslib")
    if not os.path.exists(syslib):
        os.makedirs(syslib)
        with open(os.path.join(syslib, "__init__.py"), "wt") as f:
            f.write(" ")
    l.release()
