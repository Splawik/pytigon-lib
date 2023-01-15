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

import binascii
import datetime
import re
import sys
import gettext
import uuid
import functools
import io
import mimetypes

import fs.path
from django.core.cache import cache
from django.core.files.storage import default_storage
from django.http import HttpResponse

from fs.osfs import OSFS

from pytigon_lib.schfs.vfstools import norm_path, automount, convert_file
from pytigon_lib.schtable.table import Table

from pytigon_lib.schtools import schjson
from pytigon_lib.schtools.tools import bencode, bdecode, is_null


from django_q.tasks import async_task, result

_ = gettext.gettext


def str_cmp(x, y, ts):
    (id, znak) = ts[0]
    if x[id] == ".." or (type(x[id]) == tuple and x[id][0] == ".."):
        return -1
    if y[id] == ".." or (type(y[id]) == tuple and y[id][0] == ".."):
        return 1
    if type(x[id]) == str and type(y[id]) == tuple:
        return 1
    elif type(x[id]) == tuple and type(y[id]) == str:
        return -1
    try:
        if x[id] > y[id]:
            return znak
        if x[id] < y[id]:
            return -1 * znak
        if len(ts) > 1:
            return str_cmp(x, y, ts[1:])
        else:
            return 0
    except:
        print("X: ", x[id])
        print("Y: ", y[id])
        return 0


class VfsTable(Table):
    def __init__(self, folder):
        self.var_count = -1
        # self.folder = replace_dot(folder).replace('%20', ' ')
        self.folder = norm_path(folder)

        self.auto_cols = []
        self.col_length = [10, 10, 10]
        self.col_names = ["ID", "Name", "Size", "Created"]
        self.col_types = ["int", "str", "int", "datetime"]
        self.default_rec = ["", 0, None]
        self.task_href = None

    def set_task_href(self, href):
        self.task_href = href

    def _size_to_color(self, size):
        colors = (
            (1024, "#fff"),
            (1048576, "#fdd"),
            (1073741824, "#f99,#FFF"),
            (1099511627776, "#000,#FFF"),
        )
        for pos in colors:
            if size < pos[0]:
                return pos[1]
        return colors[-1][1]

    def _time_to_color(self, time):
        if time:
            size = (datetime.datetime.today() - time).days
            colors = (
                (1, "#FFF,#F00"),
                (7, "#efe"),
                (31, "#dfd"),
                (365, "#cfc"),
                (365, "#000,#FFF"),
            )
            for pos in colors:
                if size < pos[0]:
                    return pos[1]
            return colors[-1][1]
        else:
            return "#FFF,#F00"

    def _get_table(self, value=None):
        try:
            f = default_storage.fs.listdir(automount(self.folder))
        except:
            return []

        elements = []
        files = []
        if value:
            cmp = re.compile(value, re.IGNORECASE)
        else:
            cmp = None

        if self.folder != "/":
            f = [
                "..",
            ] + f
        for p in f:
            pos = fs.path.join(self.folder, p)
            if default_storage.fs.isdir(pos) or p.lower().endswith(".zip"):
                if cmp and cmp.match(p) or not cmp:
                    try:
                        id = bencode(pos)
                        info = default_storage.fs.getdetails(pos)
                        # if not ha'created_time' in info:
                        #    info['created_time'] = ''
                        elements.append(
                            [
                                id,
                                (p, ",#fdd"),
                                "",
                                # (info['created_time'], ',,#f00,s'),
                                (info.modified.replace(tzinfo=None), ",,#f00,s"),
                                info.raw,
                                {
                                    "edit": (
                                        "tableurl",
                                        "../../%s/_/" % id,
                                        _("Change folder"),
                                    )
                                },
                            ]
                        )
                    except Exception as exception:
                        print(str(exception))
            else:
                files.append((p, pos))
        for pp in files:
            p = pp[0]
            pos = pp[1]
            if cmp and cmp.match(p) or not cmp:
                try:
                    id = bencode(pos)
                    info = default_storage.fs.getdetails(pos)
                    # size = info['size']
                    # ctime = info['created_time']
                    size = info.size
                    ctime = info.modified.replace(tzinfo=None)
                    elements.append(
                        [
                            id,
                            p,
                            (size, ">," + self._size_to_color(size)),
                            (ctime, "," + self._time_to_color(ctime)),
                            info.raw,
                            {"edit": ("command", "../../%s/_/" % id, _("Open file"))},
                        ]
                    )
                except Exception as exception:
                    print(str(exception))

        return elements

    def page(self, nr, sort=None, value=None):
        key = "FOLDER_" + bencode(self.folder) + "_TAB"
        tabvalue = None
        if tabvalue:
            tab = tabvalue
        else:
            tab = self._get_table(value)[nr * 256 : (nr + 1) * 256]
            cache.set(key + "::" + is_null(value, ""), tab, 300)

        self.var_count = len(tab)
        if sort != None:
            s = sort.split(",")
            ts = []
            for pos in s:
                if pos != "":
                    id = 0
                    znak = 0
                    if pos[0] == "-":
                        id = self.col_names.index(pos[1:])
                        znak = -1
                    else:
                        id = self.col_names.index(pos)
                        znak = 1
                    ts.append((id, znak))

            def _cmp(x, y):
                return str_cmp(x, y, ts)

            tab.sort(key=functools.cmp_to_key(_cmp))
        return tab

    def count(self, value):
        key = "FOLDER_" + bencode(self.folder) + "_COUNT"
        # countvalue = cache.get(key + '::' + is_null(value, ''))
        countvalue = None

        if countvalue:
            return countvalue
        else:
            countvalue = len(self._get_table(value))
            cache.set(key + "::" + is_null(value, ""), countvalue, 300)
            return countvalue

        return len(self._get_table(value))

    def insert_rec(self, rec):
        pass

    def update_rec(self, rec):
        pass

    def delete_rec(self, nr):
        pass

    def auto(self, col_name, col_names, rec):
        pass

    def exec_command(self, value):
        """exec:
        COPY(source_folder, dest_folder, files, mask);
        DEL(source_folder, files);
        MKDIR(source_folder, folder_name);
        MOVE(source_folder, dest_folder, files, mask):
        RENAME(source_path, new_name);
        NEWFILE(source_path, new_name);
        """

        thread_commands = ("COPY", "MOVE", "DELETE")
        if value[0] in thread_commands:
            parm = {}
            parm["cmd"] = value[0]
            if value[1][1]:
                parm["files"] = [bdecode(v) for v in value[1][1]]
            else:
                parm["files"] = [
                    bdecode(value[1][0]),
                ]
            if len(value[2]) > 1:
                parm["dest"] = bdecode(value[2][1])

            publish_id = uuid.uuid4().hex
            task_id = async_task(
                "schcommander.tasks.vfs_action", task_publish_id=publish_id, param=parm
            )
            c = {"task_id": task_id, "process_id": "vfs_action__" + publish_id}
        elif value[0] == "MKDIR":
            path = bdecode(value[2][0])
            name = bdecode(value[2][1])
            default_storage.fs.makedir(path + "/" + name)
            c = {}
        elif value[0] == "NEWFILE":
            path = bdecode(value[2][0])
            name = bdecode(value[2][1])
            with default_storage.fs.open(path + "/" + name, "wb") as f:
                pass
            # default_storage.fs.createfile(path+"/"+name)
            c = {}
        elif value[0] == "RENAME":
            source = bdecode(value[1][0])
            path = bdecode(value[2][0])
            name = bdecode(value[2][1])
            default_storage.fs.move(source, path + "/" + name)
            c = {}
        else:
            c = {}
        return c


def vfstable_view(request, folder, value=None):
    if request.POST:
        p = request.POST.copy()
        d = {}
        for (key, val) in list(p.items()):
            if key != "csrfmiddlewaretoken":
                d[str(key)] = schjson.loads(val)
    else:
        d = {}
    if value and value != "" and value != "_":
        d["value"] = bdecode(value)
    if folder and folder != "" and folder != "_":
        folder2 = bdecode(folder)
    else:
        folder2 = "/"
    # folder2 = replace_dot(folder2)
    folder2 = norm_path(folder2)
    tabview = VfsTable(folder2)
    retstr = tabview.command(d)
    return HttpResponse(retstr)


def vfsopen(request, file):
    try:
        try:
            file2 = bdecode(file)
        except:
            file2 = bdecode(file)
        plik = default_storage.fs.open(automount(file2), "rb")
        buf = plik.read()
        plik.close()
    except:
        buf = ""

    headers = {}
    if file2.endswith(".pdf"):
        headers = {
            "Content-Type": "application/pdf",
            "Content-Disposition": 'attachment; filename="file.pdf"',
        }
    elif file2.endswith(".spdf"):
        headers = {
            "Content-Type": "application/spdf",
            "Content-Disposition": 'attachment; filename="file.spdf"',
        }
    elif file2.endswith(".docx"):
        headers = {
            "Content-Type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "Content-Disposition": 'attachment; filename="file.docx"',
        }
    elif file2.endswith(".xlsx"):
        headers = {
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "Content-Disposition": 'attachment; filename="file.xlsx"',
        }
    else:
        ext = "." + file2.split(".")[-1]
        if ext in mimetypes.types_map:
            mt = mimetypes.types_map[ext]
            headers = {
                "Content-Type": mt,
                "Content-Disposition": 'attachment; filename="file' + ext + '"',
            }

    return HttpResponse(buf, headers=headers)


def vfsopen_page(request, file, page):
    try:
        file2 = bdecode(file)
        page2 = int(page)
        plik = default_storage.fs.open(automount(file2), "rb")
        try:
            plik.seek(page2 * 4096)
            buf = binascii.hexlify(plik.read(4096))
            plik.close()
        except:
            buf = ""
    except:
        buf = ""
    return HttpResponse(buf)


def vfssave(request, file):
    buf = "ERROR"
    plik = None
    if request.POST:
        try:
            data = request.POST["data"]
            file2 = bdecode(file)
            plik = default_storage.fs.open(automount(file2), "w")
            plik.write(data)
            plik.close()
            x = file2.split("/")[-1].split(".")
            if len(x) > 2:
                if x[-1].lower() in ("imd", "md", "ihtml", "html"):
                    if x[-2].lower() in ("html", "pdf", "spdf", "docx", "xlsx"):
                        file3 = file2.replace("." + x[-1], "")
                        convert_file(file2, file3)
            buf = "OK"
        except:
            buf = "ERROR: " + str(sys.exc_info()[0])
            if plik:
                plik.close()
    return HttpResponse(buf)


def vfsview(request, file):
    buf = "ERROR"
    # try:
    if True:
        file2 = bdecode(file)
        if file2.endswith(".ithm") or file2.endswith(".imd") or file2.endswith(".md"):
            return vfsconvert(request, file, "html")
        with default_storage.fs.open(automount(file2), "r") as f:
            buf = f.read()
    # except:
    #    buf = "ERROR: " + str(sys.exc_info()[0])
    return buf


# input formats: ihtml, html, imd, md
# output formats: html, pdf, xlsx, docx
def vfsconvert(request, file, output_format="pdf"):
    file2 = bdecode(file)
    output_stream = io.BytesIO()
    convert_file(file2, output_stream, output_format=output_format)
    return output_stream.getvalue()
