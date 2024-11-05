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
from pytigon_lib.schtools.main_paths import get_main_paths
from pytigon_lib.schtools.env import get_environ


def init_paths(prj_name=None, env_path=None):
    if env_path:
        get_environ(env_path)

    cfg = get_main_paths(prj_name)

    tmp = []
    for pos in sys.path:
        if pos not in tmp:
            if not pos.startswith("."):
                tmp.append(pos)
    sys.path = tmp

    from pytigon_lib.schtools.platform_info import platform_name

    base_path = os.path.dirname(os.path.abspath(__file__))
    pname = platform_name()

    if pname == "Android":
        p = os.path.abspath(os.path.join(base_path, "..", "_android"))
        p2 = os.path.abspath(os.path.join(base_path, "..", "ext_lib"))
        if p not in sys.path:
            sys.path.insert(0, p)
        if p2 not in sys.path:
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

        if p not in sys.path:
            sys.path.insert(0, p)
        if p2 not in sys.path:
            sys.path.append(p2)

    if cfg["SERW_PATH"] not in sys.path:
        sys.path.append(cfg["SERW_PATH"])
    if cfg["ROOT_PATH"] not in sys.path:
        sys.path.append(cfg["ROOT_PATH"])
    if cfg["PRJ_PATH_ALT"] not in sys.path:
        sys.path.append(cfg["PRJ_PATH_ALT"])

    p1 = os.path.join(cfg["ROOT_PATH"], "ext_lib")
    p2 = os.path.join(cfg["ROOT_PATH"], "appdata", "plugins")
    p3 = os.path.join(cfg["DATA_PATH"], "plugins")
    if prj_name:
        p4 = os.path.join(cfg["DATA_PATH"], prj_name, "syslib")
        p5 = os.path.join(cfg["PRJ_PATH"], prj_name, "prjlib")
        if p5 not in sys.path and os.path.exists(p5):
            sys.path.append(p5)

    if p1 not in sys.path:
        sys.path.append(p1)
    if p2 not in sys.path:
        sys.path.append(p2)
    if p3 not in sys.path:
        sys.path.append(p3)
    if prj_name and p4 not in sys.path:
        sys.path.append(p4)

    if prj_name:
        prjlib_path = os.path.join(cfg["DATA_PATH"], prj_name, "prjlib")
        if prjlib_path not in sys.path:
            sys.path.append(prjlib_path)
