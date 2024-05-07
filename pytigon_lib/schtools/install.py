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
# license: "LGPL 3.0"
# version: "0.1a"

import datetime
import zipfile
import io

from pytigon_lib.schdjangoext.django_manage import *
from pytigon_lib.schfs.vfstools import extractall
from pytigon_lib.schtools.process import py_run
from pytigon_lib.schtools.main_paths import get_prj_name


def install():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings_app")
    from django.conf import settings

    prj_name = get_prj_name()
    data_path = settings.DATA_PATH
    prj_path = settings.PRJ_PATH
    app_data_path = os.path.join(data_path, prj_name)
    db_path = os.path.join(app_data_path, prj_name + ".db")

    upgrade = False

    if os.path.exists(db_path):
        upgrade = True
    if "local" in settings.DATABASES:
        db_profile = "local"
    else:
        db_profile = "default"

    db_path_new = os.path.join(app_data_path, prj_name + ".new")

    if upgrade:
        try:
            cmd(["migrate", "--database", db_profile])
        except:
            print("Migration for database: " + db_profile + " - fails")
    else:
        os.rename(db_path_new, db_path)

    if db_profile != "default":
        try:
            cmd(["migrate", "--database", "default"])
        except:
            print("Migration for database: defautl - fails")

    if not upgrade:
        if db_profile != "default":
            temp_path = os.path.join(data_path, "temp")
            if not os.path.exists(temp_path):
                os.mkdir(temp_path)
            json_path = os.path.join(temp_path, prj_name + ".json")
            parameters = [
                "dumpdata",
                "--database",
                db_profile,
                "--format",
                "json",
                "--indent",
                "4",
            ]
            do_not_export = [
                "auth",
                "contenttypes",
                "sessions",
                "sites",
                "admin",
                "socialaccount",
                "account",
                "schreports",
            ]
            for item in do_not_export:
                for app in settings.INSTALLED_APPS:
                    if item in app:
                        parameters.append("-e")
                        parameters.append(item)
                        break

            parameters.append("--output")
            parameters.append("json_path")
            parameters.append("--traceback")
            print(parameters)
            cmd(parameters)

            cmd(["loaddata", "--database", "default", json_path, "--traceback"])
            from django.contrib.auth.models import User

            User.objects.db_manager("default").create_superuser(
                "auto", "auto@pytigon.com", "anawa"
            )

    # ret = make(data_path, prj_path, prj_name)
    # if ret:
    #    for pos in ret:
    #        print(pos)


def export_to_db(withoutapp=None, to_local_db=True):
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings_app")
    from django.conf import settings

    if "local" in settings.DATABASES:
        prj_name = settings.PRJ_NAME
        data_path = settings.DATA_PATH
        app_data_path = os.path.join(data_path, prj_name)
        # db_path = os.path.join(app_data_path, prj_name + ".db")
        db_path = settings.DATABASES["local"]["NAME"]

        temp_path = os.path.join(data_path, "temp")
        if not os.path.exists(temp_path):
            os.mkdir(temp_path)
        json_path = os.path.join(temp_path, prj_name + ".json")

        if to_local_db:
            parameters = [
                "dumpdata",
                "--database",
                "default",
                "--format",
                "json",
                "--indent",
                "4",
            ]
        else:
            parameters = [
                "dumpdata",
                "--database",
                "local",
                "--format",
                "json",
                "--indent",
                "4",
            ]

        if withoutapp is None or "sys" in withoutapp:
            do_not_export = [
                "auth",
                "contenttypes",
                "sessions",
                "sites",
                "admin",
                "socialaccount",
                "account",
            ]
        else:
            do_not_export = []

        if withoutapp:
            for item in withoutapp:
                if item:
                    do_not_export.append(item)

        for item in do_not_export:
            for app in settings.INSTALLED_APPS:
                if type(app) != str:
                    app = app.name
                if item in app:
                    parameters.append("-e")
                    parameters.append(item)
                    break
        parameters.append("--output")
        parameters.append(json_path)
        parameters.append("--traceback")
        cmd(parameters)

        if to_local_db:
            if os.path.exists(db_path):
                os.rename(
                    db_path,
                    db_path
                    + "."
                    + datetime.datetime.now().strftime("%Y%m%d%H%M%S")
                    + ".bak",
                )
            cmd(["migrate", "--database", "local"])
        else:
            cmd(["migrate"])

        if to_local_db:
            cmd(["loaddata", "--database", "local", json_path, "--traceback"])
        else:
            cmd(["loaddata", "--database", "default", json_path, "--traceback"])

        if to_local_db:
            from django.contrib.auth.models import User

            User.objects.db_manager("local").create_superuser(
                "auto", "auto@pytigon.com", "anawa"
            )


def export_to_local_db(withoutapp=None):
    return export_to_db(withoutapp, to_local_db=True)


def import_from_local_db(withoutapp=None, to_local_db=True):
    return export_to_db(withoutapp, to_local_db=False)


class Ptig:
    def __init__(self, ptig_path_or_file):
        # if type(ptig_path_or_file) == str:
        #    self.archive = zipfile.ZipFile(ptig_path_or_file, "r")
        # else:
        #    self.archive = zipfile.ZipFile(ptig_path_or_file)
        if type(ptig_path_or_file) == str:
            with open(ptig_path_or_file, "rb") as f:
                zip_content = f.read()
        else:
            zip_content = ptig_path_or_file.read()

        zip_content = zip_content.split(b"\n", 1)[1]

        self.archive = zipfile.ZipFile(io.BytesIO(zip_content))

        namelist = self.archive.namelist()
        self.prj_name = None
        self.version = None
        self.meta_path = None
        for name in namelist:
            if ".dist-info" in name:
                self.meta_path = name.split("/")[0]
                x = self.meta_path.split(".")[0]
                x2 = x.split("-", 1)
                if len(x2) > 1:
                    self.version = x2[1]
                else:
                    self.version = "latest"
                self.prj_name = x2[0]
                break
        self.extract_to = None

    def is_ok(self):
        if self.prj_name:
            return True
        else:
            return False

    def get_license(self):
        ret = self.archive.read(self.prj_name + "/LICENSE").decode("utf-8")
        if ret:
            return ret
        return ""

    def get_readme(self):
        ret = self.archive.read(self.prj_name + "/README.md").decode("utf-8")
        if ret:
            return ret
        return ""

    def get_db(self):
        return self.archive.read(self.meta_path + "/" + self.prj_name + ".db")

    def extract_ptig(self):
        import pytigon.schserw.settings
        from django.conf import settings

        if hasattr(pytigon.schserw.settings, "_PRJ_PATH_ALT"):
            base_path = os.path.join(pytigon.schserw.settings._PRJ_PATH_ALT)
        else:
            base_path = os.path.join(settings.PRJ_PATH_ALT)

        ret = []
        ret.append("Install file: " + self.prj_name)
        test_update = True

        extract_to = os.path.join(base_path, self.prj_name)
        ret.append("install to: " + extract_to)

        if not os.path.exists(base_path):
            os.mkdir(base_path)
            # os.mkdir(settings.PRJ_PATH)
        if not os.path.exists(extract_to):
            os.mkdir(extract_to)
            test_update = False

        self.extract_to = extract_to

        zipname = (
            datetime.datetime.now()
            .isoformat("_")[:19]
            .replace(":", "")
            .replace("-", "")
        )
        zipname2 = os.path.join(extract_to, zipname + ".zip")
        if test_update:
            backup_zip = zipfile.ZipFile(zipname2, "a")
            exclude = [
                ".*settings_local.py.*",
            ]
        else:
            backup_zip = None
            exclude = None

        extractall(
            self.archive,
            base_path,
            backup_zip=backup_zip,
            exclude=exclude,
            only_path=self.prj_name + "/",
            backup_exts=[
                "py",
                "txt",
                "wsgi",
                "asgi",
                "ihtml",
                "htlm",
                "css",
                "js",
                "prj",
            ],
        )

        if backup_zip:
            backup_zip.close()

        src_db = self.get_db()
        if src_db:
            ret.append("Synchronize database:")
            dest_path_db = os.path.join(settings.DATA_PATH, self.prj_name)
            dest_db = os.path.join(dest_path_db, self.prj_name + ".db")

            if not os.path.exists(settings.DATA_PATH):
                os.mkdir(settings.DATA_PATH)
            if not os.path.exists(dest_path_db):
                os.mkdir(dest_path_db)
            if not os.path.exists(dest_db):
                with open(dest_path_db, "wb") as f:
                    f.write(src_db)

            (ret_code, output, err) = py_run(
                [os.path.join(extract_to, "manage.py"), "postinstallation"]
            )

            if output:
                for pos in output:
                    ret.append(pos)
            if err:
                ret.append("ERRORS:")
                for pos in err:
                    ret.append(pos)
        return ret

    def close(self):
        self.archive.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()
