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

# author: "Sławomir Chołaj (slawomir.cholaj@gmail.com)"dd
# copyright: "Copyright (C) ????/2012 Sławomir Chołaj"
# license: "LGPL 3.0"
# version: "0.1a"

import sys
import os
from os import environ
from pytigon_lib.schtools.main_paths import get_main_paths
from pytigon_lib.schtools.env import get_environ


def init_paths(prj_name=None, env_path=None):
    if env_path:
        get_environ(env_path)

    cfg = get_main_paths(prj_name)

    tmp = []
    for pos in sys.path:
        if not pos in tmp:
            if not pos.startswith("."):
                tmp.append(pos)
    sys.path = tmp

    from pytigon_lib.schtools.platform_info import platform_name

    base_path = os.path.dirname(os.path.abspath(__file__))
    pname = platform_name()

    if pname == "Android":
        p = os.path.abspath(os.path.join(base_path, "..", "_android"))
        p2 = os.path.abspath(os.path.join(base_path, "..", "ext_lib"))
        if not p in sys.path:
            sys.path.insert(0, p)
        if not p2 in sys.path:
            sys.path.append(p2)
    else:
        if pname == "Windows":
            p = os.path.abspath(
                os.path.join(base_path, "..", "python" "lib", "site-packages")
            )
        else:
            p = os.path.abspath(
                os.path.join(
                    base_path,
                    "..",
                    "python",
                    "lib",
                    "python%d.%d/site-packages"
                    % (sys.version_info[0], sys.version_info[1]),
                )
            )

        p2 = os.path.abspath(os.path.join(base_path, "..", "ext_lib"))

        if not p in sys.path:
            sys.path.insert(0, p)
        if not p2 in sys.path:
            sys.path.append(p2)

    if not cfg["SERW_PATH"] in sys.path:
        sys.path.append(cfg["SERW_PATH"])
    if not cfg["ROOT_PATH"] in sys.path:
        sys.path.append(cfg["ROOT_PATH"])
    if not cfg["PRJ_PATH_ALT"] in sys.path:
        sys.path.append(cfg["PRJ_PATH_ALT"])

    p1 = os.path.join(cfg["ROOT_PATH"], "ext_lib")
    p2 = os.path.join(cfg["ROOT_PATH"], "appdata", "plugins")
    p3 = os.path.join(cfg["DATA_PATH"], "plugins")
    if prj_name:
        p4 = os.path.join(cfg["DATA_PATH"], prj_name, "syslib")

    if not p1 in sys.path:
        sys.path.append(p1)
    if not p2 in sys.path:
        sys.path.append(p2)
    if not p3 in sys.path:
        sys.path.append(p3)
    if prj_name and not p4 in sys.path:
        sys.path.append(p4)

    if prj_name:
        prjlib_path = os.path.join(cfg["DATA_PATH"], prj_name, "prjlib")
        if not prjlib_path in sys.path:
            sys.path.append(prjlib_path)


#    environ['LD_LIBRARY_PATH'] = os.path.join(cfg['DATA_PATH'], "ext_prg", "tcc")
