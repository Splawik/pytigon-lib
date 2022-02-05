#!/usr/bin/python

# -*- coding: utf-8 -*-

from django.core.files.storage import default_storage


def filesystemcmd(cproxy=None, **kwargs):
    """bacground tasks related to file system"""

    if cproxy:
        cproxy.send_event("start")

    param = kwargs["param"]
    cmd = param["cmd"]
    files = param["files"]
    if "dest" in param:
        dest = param["dest"] + "/"
    if cmd == "DELETE":
        for f in files:
            try:
                if default_storage.fs.isfile(f):
                    default_storage.fs.remove(f)
                else:
                    default_storage.fs.removetree(f)
            except Exception as exception:
                print(str(exception))
    elif cmd == "COPY":
        for f in files:
            try:
                name = f.rsplit("/", 1)[-1]
                if default_storage.fs.isfile(f):
                    default_storage.fs.copy(f, dest + name, overwrite=True)
                else:
                    default_storage.fs.copydir(
                        f, dest + name, overwrite=True, ignore_errors=True
                    )
            except:
                pass
    elif cmd == "MOVE":
        for f in files:
            try:
                name = f.rsplit("/", 1)[-1]
                if default_storage.fs.isfile(f):
                    default_storage.fs.move(f, dest + name, overwrite=True)
                else:
                    default_storage.fs.movedir(
                        f, dest + name, overwrite=True, ignore_errors=True
                    )
            except:
                pass
    if cproxy:
        cproxy.send_event("stop")
