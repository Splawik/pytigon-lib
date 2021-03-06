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
#license: "LGPL 3.0"
#version: "0.1a"

import os
import datetime
import zipfile
from shutil import move
from pathlib import Path

#from django.conf import settings
from pytigon.schserw import settings
from pytigon_lib.schdjangoext.django_manage import *
from pytigon_lib.schfs.vfstools import extractall
from pytigon_lib.schtools.process import py_run
from pytigon_lib.schtools.cc import make
from pytigon_lib.schtools.main_paths import get_prj_name

def install():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings_app")
    from django.conf import settings as dsettings
    prj_name = get_prj_name()
    data_path = settings.DATA_PATH
    root_path = settings.ROOT_PATH
    prj_path = settings.PRJ_PATH
    app_data_path = os.path.join(data_path, prj_name)
    db_path = os.path.join(app_data_path, prj_name+".db")
    compiler_base_path = os.path.join(data_path, "ext_prg")

    upgrade = False

    if os.path.exists(db_path):
        upgrade = True
    if 'local' in dsettings.DATABASES:
        db_profile = 'local'
    else:
        db_profile = 'default'

    db_path_new = os.path.join(app_data_path, prj_name + ".new")

    if upgrade:
        try:
            cmd(['migrate', '--database', db_profile])
        except:
            print("Migration for database: " + db_profile + " - fails")
    else:
        os.rename(db_path_new, db_path)

    if db_profile != 'default':
        try:
            cmd(['migrate', '--database', 'default'])
        except:
            print("Migration for database: defautl - fails")

    if not upgrade:
        if db_profile != 'default':
            temp_path = os.path.join(data_path, 'temp')
            if not os.path.exists(temp_path):
                os.mkdir(temp_path)
            json_path = os.path.join(temp_path, prj_name + '.json')
            print(json_path)
            cmd(['dumpdata', '--database', db_profile, '--format', 'json', '--indent', '4',
                 '-e', 'auth', '-e', 'contenttypes', '-e', 'sessions', '-e', 'sites', '-e', 'admin',
                 '--output', json_path])
            cmd(['loaddata', '--database', 'default', json_path])
            from django.contrib.auth.models import User
            User.objects.db_manager('default').create_superuser('auto', 'auto@pytigon.com', 'anawa')

    ret = make(data_path, prj_path)
    if ret:
        for pos in ret:
            print(pos)

def export_to_local_db():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings_app")
    if 'local' in settings.DATABASES:
        db_profile = 'local'
    else:
        db_profile = 'default'

    if db_profile != 'default':
        prj_name = settings.PRJ_NAME
        data_path = settings.DATA_PATH
        app_data_path = os.path.join(data_path, prj_name)
        db_path = os.path.join(app_data_path, prj_name+".db")

        if os.path.exists(db_path):
            os.rename(db_path, db_path + "." + datetime.datetime.now().strftime('%Y%m%d%H%M%S') + ".bak")

        cmd(['migrate', '--database', db_profile])

        temp_path = os.path.join(data_path, 'temp')
        if not os.path.exists(temp_path):
            os.mkdir(temp_path)
        json_path = os.path.join(temp_path, prj_name + '.json')
        cmd(['dumpdata', '--database', 'default', '--format', 'json', '--indent', '4',
             '-e', 'auth', '-e', 'contenttypes', '-e', 'sessions', '-e', 'sites', '-e', 'admin',
             '--output', json_path])
        cmd(['loaddata', '--database', db_profile, json_path])
        from django.contrib.auth.models import User
        User.objects.db_manager(db_profile).create_superuser('auto', 'auto@pytigon.com', 'anawa')



def extract_ptig(zip_file, name):

    ret = []
    ret.append("Install file: " + name)
    test_update = True

    extract_to = os.path.join(settings.PRJ_PATH, name)
    ret.append("install to: " + extract_to)

    if not os.path.exists(settings.PRJ_PATH):
        os.mkdir(settings.PRJ_PATH)
    if not os.path.exists(extract_to):
        os.mkdir(extract_to)
        test_update = False

    zipname = datetime.datetime.now().isoformat('_')[:19].replace(':', '').replace('-', '')
    zipname2 = os.path.join(extract_to, zipname + ".zip")
    if test_update:
        backup_zip = zipfile.ZipFile(zipname2, 'a')
        exclude = ['.*settings_local.py.*', ]
    else:
        backup_zip = None
        exclude = None

    extractall(zip_file, extract_to, backup_zip=backup_zip, exclude=exclude,
               backup_exts=['py', 'txt', 'wsgi', 'ihtml', 'htlm', 'css', 'js', ])

    if backup_zip:
        backup_zip.close()
    zip_file.close()

    src_db = os.path.join(extract_to, name + ".db")
    if os.path.exists(src_db):
        ret.append("Synchronize database:")
        dest_path_db = os.path.join(settings.DATA_PATH, name)

        if not os.path.exists(settings.DATA_PATH):
            os.mkdir(settings.DATA_PATH)
        if not os.path.exists(dest_path_db):
            os.mkdir(dest_path_db)
        dest_db = os.path.join(dest_path_db, name + ".db")
        if not os.path.exists(dest_db):
            move(src_db, os.path.join(dest_path_db, name + ".new"))

        (ret_code, output, err) = py_run([os.path.join(extract_to, 'manage.py'), 'post_installation'])

        if output:
            for pos in output:
                ret.append(pos)
        if err:
            ret.append("ERRORS:")
            for pos in err:
                ret.append(pos)

    return ret
