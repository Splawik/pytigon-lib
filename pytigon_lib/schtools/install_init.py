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
from pytigon_lib.schfs import extractall
import zipfile
from distutils.dir_util import copy_tree
import configparser
from pytigon_lib.schtools.process import py_manage
from pytigon_lib.schtools.cc import make


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
    return False


def init(prj, root_path, data_path, prj_path, static_app_path, paths=None):
    _root_path = os.path.normpath(root_path)
    _data_path = os.path.normpath(data_path)
    _prj_path = os.path.normpath(prj_path)
    _static_app_path = os.path.normpath(static_app_path)
    _base_compiler_path = os.path.join(_data_path, "ext_prg")
    test1 = 0 if os.path.exists(_prj_path) else 1
    test2 = 0 if os.path.exists(_data_path) else 1
    test3 = 0 if os.path.exists(_static_app_path) else 1

    if not test2:
        if upgrade_test(
            os.path.join(os.path.join(_root_path, "install"), ".pytigon.zip"),
            _data_path,
        ):
            test2 = 2
            print("Upgrade data")

    if test2:
        zip_file2 = os.path.join(os.path.join(_root_path, "install"), ".pytigon.zip")
        if not os.path.exists(_data_path):
            os.makedirs(_data_path)
        if os.path.exists(zip_file2):
            if test2 == 2:
                extractall(zipfile.ZipFile(zip_file2), _data_path, exclude=[".*\.db"])
            else:
                extractall(zipfile.ZipFile(zip_file2), _data_path)
        if not os.path.exists(os.path.join(_data_path, "media")):
            media_path = os.path.join(os.path.join(_data_path, "media"))
            os.makedirs(media_path)
            os.makedirs(os.path.join(media_path, "filer_public"))
            os.makedirs(os.path.join(media_path, "filer_private"))
            os.makedirs(os.path.join(media_path, "filer_public_tumbnails"))
            os.makedirs(os.path.join(media_path, "filer_private_thumbnails"))
        prjs = [ff for ff in os.listdir(_prj_path) if not ff.startswith("_")]

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
        os.chdir(tmp)
    if test2 == 2:
        pass

    if test3:
        p2 = os.path.join(os.path.join(_root_path, "static"), "app")
        if os.path.exists(p2):
            copy_tree(p2, _static_app_path, preserve_mode=0, preserve_times=0)

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

    prjlib = os.path.join(os.path.join(_prj_path, prj), "prjlib")
    if os.path.exists(prjlib):
        if not prjlib in sys.path:
            sys.path.append(prjlib)
        if test1 or test2 or test3:
            ret = make(_data_path, os.path.join(_prj_path, prj))
            if ret:
                for pos in ret:
                    print(pos)
