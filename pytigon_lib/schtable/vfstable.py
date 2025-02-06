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
    """Compare two strings based on the given sorting criteria."""
    (id, znak) = ts[0]
    if x[id] == ".." or (isinstance(x[id], tuple) and x[id][0] == ".."):
        return -1
    if y[id] == ".." or (isinstance(y[id], tuple) and y[id][0] == ".."):
        return 1
    if isinstance(x[id], str) and isinstance(y[id], tuple):
        return 1
    elif isinstance(x[id], tuple) and isinstance(y[id], str):
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
    except Exception as e:
        print(f"Error comparing {x[id]} and {y[id]}: {e}")
        return 0


class VfsTable(Table):
    """A table representation of a virtual file system."""

    def __init__(self, folder):
        """Initialize the VfsTable with the given folder."""
        self.var_count = -1
        self.folder = norm_path(folder)
        self.auto_cols = []
        self.col_length = [10, 10, 10]
        self.col_names = ["ID", "Name", "Size", "Created"]
        self.col_types = ["int", "str", "int", "datetime"]
        self.default_rec = ["", 0, None]
        self.task_href = None

    def set_task_href(self, href):
        """Set the task href."""
        self.task_href = href

    def _size_to_color(self, size):
        """Convert file size to a color code."""
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
        """Convert file modification time to a color code."""
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
        """Get the table data for the current folder."""
        try:
            f = default_storage.fs.listdir(automount(self.folder))
        except Exception as e:
            print(f"Error listing directory: {e}")
            return []

        elements = []
        files = []
        cmp = re.compile(value, re.IGNORECASE) if value else None

        if self.folder != "/":
            f = [".."] + f

        for p in f:
            pos = fs.path.join(self.folder, p)
            if default_storage.fs.isdir(pos) or p.lower().endswith(".zip"):
                if not cmp or cmp.match(p):
                    try:
                        id = bencode(pos)
                        info = default_storage.fs.getdetails(pos)
                        elements.append(
                            [
                                id,
                                (p, ",#fdd"),
                                "",
                                (info.modified.replace(tzinfo=None), ",,#f00,s"),
                                info.raw,
                                {
                                    "edit": (
                                        "tableurl",
                                        f"../../{id}/_/",
                                        _("Change folder"),
                                    )
                                },
                            ]
                        )
                    except Exception as e:
                        print(f"Error processing directory {p}: {e}")
            else:
                files.append((p, pos))

        for p, pos in files:
            if not cmp or cmp.match(p):
                try:
                    id = bencode(pos)
                    info = default_storage.fs.getdetails(pos)
                    size = info.size
                    ctime = info.modified.replace(tzinfo=None)
                    elements.append(
                        [
                            id,
                            p,
                            (size, f">,{self._size_to_color(size)}"),
                            (ctime, f",{self._time_to_color(ctime)}"),
                            info.raw,
                            {"edit": ("command", f"../../{id}/_/", _("Open file"))},
                        ]
                    )
                except Exception as e:
                    print(f"Error processing file {p}: {e}")

        return elements

    def page(self, nr, sort=None, value=None):
        """Get a page of the table data."""
        key = f"FOLDER_{bencode(self.folder)}_TAB"
        tab = self._get_table(value)[nr * 256 : (nr + 1) * 256]
        cache.set(f"{key}::{is_null(value, '')}", tab, 300)

        self.var_count = len(tab)
        if sort:
            s = sort.split(",")
            ts = []
            for pos in s:
                if pos:
                    id = (
                        self.col_names.index(pos[1:])
                        if pos[0] == "-"
                        else self.col_names.index(pos)
                    )
                    znak = -1 if pos[0] == "-" else 1
                    ts.append((id, znak))

            def _cmp(x, y):
                return str_cmp(x, y, ts)

            tab.sort(key=functools.cmp_to_key(_cmp))
        return tab

    def count(self, value):
        """Get the count of items in the table."""
        key = f"FOLDER_{bencode(self.folder)}_COUNT"
        countvalue = len(self._get_table(value))
        cache.set(f"{key}::{is_null(value, '')}", countvalue, 300)
        return countvalue

    def insert_rec(self, rec):
        """Insert a record into the table."""
        pass

    def update_rec(self, rec):
        """Update a record in the table."""
        pass

    def delete_rec(self, nr):
        """Delete a record from the table."""
        pass

    def auto(self, col_name, col_names, rec):
        """Automatically fill a column."""
        pass

    def exec_command(self, value):
        """Execute a command on the table."""
        thread_commands = ("COPY", "MOVE", "DELETE")
        if value[0] in thread_commands:
            parm = {"cmd": value[0]}
            parm["files"] = (
                [bdecode(v) for v in value[1][1]]
                if value[1][1]
                else [bdecode(value[1][0])]
            )
            if len(value[2]) > 1:
                parm["dest"] = bdecode(value[2][1])

            publish_id = uuid.uuid4().hex
            task_id = async_task(
                "schcommander.tasks.vfs_action", task_publish_id=publish_id, param=parm
            )
            c = {"task_id": task_id, "process_id": f"vfs_action__{publish_id}"}
        elif value[0] == "MKDIR":
            path = bdecode(value[2][0])
            name = bdecode(value[2][1])
            default_storage.fs.makedir(f"{path}/{name}")
            c = {}
        elif value[0] == "NEWFILE":
            path = bdecode(value[2][0])
            name = bdecode(value[2][1])
            with default_storage.fs.open(f"{path}/{name}", "wb") as f:
                pass
            c = {}
        elif value[0] == "RENAME":
            source = bdecode(value[1][0])
            path = bdecode(value[2][0])
            name = bdecode(value[2][1])
            default_storage.fs.move(source, f"{path}/{name}")
            c = {}
        else:
            c = {}
        return c


def vfstable_view(request, folder, value=None):
    """Handle requests for the VFS table view."""
    if request.POST:
        d = {
            key: schjson.loads(val)
            for key, val in request.POST.items()
            if key != "csrfmiddlewaretoken"
        }
    else:
        d = {}

    if value and value not in ("", "_"):
        d["value"] = bdecode(value)
    folder2 = norm_path(bdecode(folder)) if folder and folder not in ("", "_") else "/"
    tabview = VfsTable(folder2)
    retstr = tabview.command(d)
    return HttpResponse(retstr)


def vfsopen(request, file):
    """Handle requests to open a file."""
    try:
        file2 = bdecode(file)
        with default_storage.fs.open(automount(file2), "rb") as plik:
            buf = plik.read()
    except Exception as e:
        print(f"Error opening file {file}: {e}")
        buf = b""

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
                "Content-Disposition": f'attachment; filename="file{ext}"',
            }

    return HttpResponse(buf, headers=headers)


def vfsopen_page(request, file, page):
    """Handle requests to open a specific page of a file."""
    try:
        file2 = bdecode(file)
        page2 = int(page)
        with default_storage.fs.open(automount(file2), "rb") as plik:
            plik.seek(page2 * 4096)
            buf = binascii.hexlify(plik.read(4096))
    except Exception as e:
        print(f"Error opening page {page} of file {file}: {e}")
        buf = b""
    return HttpResponse(buf)


def vfssave(request, file):
    """Handle requests to save a file."""
    buf = "ERROR"
    if request.POST:
        try:
            data = request.POST["data"]
            file2 = bdecode(file)
            with default_storage.fs.open(automount(file2), "w") as plik:
                plik.write(data)
            x = file2.split("/")[-1].split(".")
            if len(x) > 2 and x[-1].lower() in ("imd", "md", "ihtml", "html"):
                if x[-2].lower() in ("html", "pdf", "spdf", "docx", "xlsx"):
                    file3 = file2.replace(f".{x[-1]}", "")
                    convert_file(file2, file3)
            buf = "OK"
        except Exception as e:
            buf = f"ERROR: {e}"
    return HttpResponse(buf)


def vfsview(request, file):
    """Handle requests to view a file."""
    try:
        file2 = bdecode(file)
        if file2.endswith((".ithm", ".imd", ".md")):
            return vfsconvert(request, file, "html")
        with default_storage.fs.open(automount(file2), "r") as f:
            buf = f.read()
    except Exception as e:
        buf = f"ERROR: {e}"
    return HttpResponse(buf)


def vfsconvert(request, file, output_format="pdf"):
    """Handle requests to convert a file to a different format."""
    file2 = bdecode(file)
    output_stream = io.BytesIO()
    convert_file(file2, output_stream, output_format=output_format)
    return HttpResponse(output_stream.getvalue())
