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

#Pytigon - wxpython and django application framework

#author: "Slawomir Cholaj (slawomir.cholaj@gmail.com)"
#copyright: "Copyright (C) ????/2012 Slawomir Cholaj"
#license: "LGPL 3.0"t
#version: "0.1a"


import os
import sys
import platform
import requests
import tarfile
import zipfile
import io
from pytigon_lib.schtools.process import run

def check_compiler(base_path):
    tcc_dir = os.path.join(base_path, "ext_prg", "tcc")
    if platform.system() == 'Windows':
        compiler = os.path.join(tcc_dir, "tcc.exe")
    else:
        compiler = os.path.join(tcc_dir, "tcc")
    return os.path.exists(compiler)


def install_tcc(path):
    prg_path = os.path.abspath(os.path.join(path, ".."))
    if not os.path.exists(prg_path):
        os.makedirs(prg_path)

    if platform.system() != 'Windows':
        if sys.maxsize > 2 ** 32:
            url = "http://download.savannah.gnu.org/releases/tinycc/tcc-0.9.27-win64-bin.zip"
        else:
            url = "http://download.savannah.gnu.org/releases/tinycc/tcc-0.9.27-win32-bin.zip"
        r = requests.get(url, allow_redirects=True)
        with zipfile.ZipFile(io.BytesIO(r.content)) as zfile:
            zfile.extractall(prg_path)
    else:
        url = "http://download.savannah.gnu.org/releases/tinycc/tcc-0.9.27.tar.bz2"
        r = requests.get(url, allow_redirects=True)
        with tarfile.open(fileobj=io.BytesIO(r.content), mode='r:bz2') as tar:
            tar.extractall(prg_path)
        os.rename(os.path.join(prg_path, "tcc-0.9.27"), path)
        temp = os.getcwd()
        os.chdir(path)
        f = os.popen('./configure --disable-static')
        f = os.popen('make')
        os.chdir(temp)

def compile(base_path, input_file_name, output_file_name=None, pyd=True):
    tcc_dir = os.path.join(base_path, "ext_prg", "tcc")
    if not os.path.exists(tcc_dir):
        install_tcc(tcc_dir)
    include1 = os.path.join(tcc_dir, "include")
    include2 = os.path.join(include1, "python")
    tmp = os.getcwd()
    os.chdir(tcc_dir)

    if output_file_name:
        ofn = output_file_name
    else:
        if platform.system() == 'Windows':
            if pyd:
                ofn = input_file_name.replace('.c', '') + ".pyd"
            else:
                ofn = input_file_name.replace('.c', '') + ".dll"
            compiler = ".\\tcc.exe"
        else:
            ofn = input_file_name.replace('.c', '')+".so"
            compiler = "./tcc"

    cmd = [compiler, input_file_name, '-o', ofn, '-shared']
    for include in (include1, include2):
        cmd.append('-I' + include + '')

    (ret_code, output, err) = run(cmd)
    os.chdir(tmp)
    return (ret_code, output, err)
