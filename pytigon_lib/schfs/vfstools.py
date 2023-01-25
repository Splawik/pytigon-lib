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

import re
import os.path
import tempfile
import email.generator
import zipfile
import hashlib

from tempfile import NamedTemporaryFile

from django.core.files.storage import default_storage
from django.conf import settings

from pytigon_lib.schdjangoext.tools import gettempdir


def norm_path(url):
    """Normalize url"""
    ldest = []
    if url == "" or url == None:
        return ""
    url2 = url.replace(" ", "%20").replace("://", "###").replace("\\", "/")
    if not "." in url2:
        return url2.replace("###", "://").replace("%20", " ")
    lsource = url2.split("/")
    for l in lsource:
        if l == "..":
            ldest.pop()
        else:
            if l != ".":
                ldest.append(l)
    ret = None
    for l in ldest:
        if ret == None:
            ret = l
        else:
            ret = ret + "/" + l
    if ret != None:
        if ret == "":
            return "/"
        else:
            return ret.replace("###", "://").replace("%20", " ")
    else:
        return ""


def open_file(filename, mode, for_vfs=False):
    if for_vfs:
        return default_storage.fs.open(filename, mode)
    else:
        return open(filename, mode)


def open_and_create_dir(filename, mode, for_vfs=False):
    """Open file - if path doesn't exist - path is created

    Args:
        filename - path and name of file
        mode - see mode for standard python function: open
    """
    if for_vfs:
        if not default_storage.fs.exists(default_storage.fs.path.dirname(filename)):
            default_storage.fs.makedirs(default_storage.fs.path.dirname(filename))
    else:
        if not os.path.exists(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))
    return open(filename, mode, for_vfs)


def get_unique_filename(base_name=None, ext=None):
    """Get temporary file name

    Args:
        base_name - if not Null returning name contains base_name
    """
    boundary = email.generator._make_boundary()
    if base_name:
        boundary += "_" + base_name
    if ext:
        boundary += "." + ext
    return boundary


def get_temp_filename(base_name=None, ext=None, for_vfs=False):
    """Get temporary file name

    Args:
        base_name - if not Null returning name contains base_name
    """
    if for_vfs:
        return "/temp/" + get_unique_filename(base_name, ext)
    else:
        return os.path.join(settings.TEMP_PATH, get_unique_filename(base_name, ext))


def delete_from_zip(zip_name, del_file_names):
    """Delete one file from zip

    Args:
        zip_name - name of zip file
        del_file_names - name of file to delete
    """
    del_file_names2 = [pos.lower() for pos in del_file_names]

    tmpname = get_temp_filename()
    zin = zipfile.ZipFile(zip_name, "r")
    zout = zipfile.ZipFile(tmpname, "w", zipfile.ZIP_STORED)
    for item in zin.infolist():
        if not item.filename.lower() in del_file_names2:
            buffer = zin.read(item.filename)
            zout.writestr(item, buffer)
    zout.close()
    zin.close()
    os.remove(zip_name)
    os.rename(tmpname, zip_name)
    return 1


def _clear_content(b):
    return (
        b.replace(b" ", b"").replace(b"\n", b"").replace(b"\t", b"").replace(b"\r", b"")
    )


def _cmp_txt_str_content(b1, b2):
    _b1 = _clear_content(b1)
    _b2 = _clear_content(b2)
    if _b1 == _b2:
        return True
    else:
        return False


def extractall(
    zip_file,
    path=None,
    members=None,
    pwd=None,
    exclude=None,
    backup_zip=None,
    backup_exts=None,
    only_path=None,
):
    """Extract content from zip file

    Args:
        zip_file - path to zip file
        path - destination path to extract zip content
        members - if None: extract all zip members else: extract only files which are in members list
        pwd  - password for zip, can be None if password is not set
        exclude - do not extract files which are in exclude list
        backup_zip -
            Files extracted from zip can overwrite existings ones. If backup_zip is set to ZipFile object,
            this function test if new content is equal with old before overwriting. If there are diferences,
            old contents is saved to backup_zip. After operation backup_zip contains all changed files by
            extracting zip file.
        backup_exts - if  parametr is set, backed to backup_zip are only files which are on backup_ext list.
    """
    if members is None:
        members = zip_file.namelist()
    for zipinfo in members:
        if only_path:
            if not zipinfo.startswith(only_path):
                continue
        if zipinfo.endswith("/") or zipinfo.endswith("\\"):
            if not os.path.exists(path + "/" + zipinfo):
                os.makedirs(path + "/" + zipinfo)
        else:
            test = True
            if exclude:
                for pos in exclude:
                    if re.match(pos, zipinfo, re.I) != None:
                        test = False
                        break
            if test:
                if backup_zip:
                    if not backup_exts or zipinfo.split(".")[-1] in backup_exts:
                        out_name = os.path.join(path, zipinfo)
                        if os.path.exists(out_name):
                            bytes = zip_file.read(zipinfo, pwd)
                            with open(out_name, "rb") as f:
                                bytes2 = f.read()
                            if not _cmp_txt_str_content(bytes, bytes2):
                                backup_zip.writestr(zipinfo, bytes2)
                zip_file.extract(zipinfo, path, pwd)


class ZipWriter:
    """Helper class to create zip files"""

    def __init__(self, filename, basepath="", exclude=[], sha256=False):
        """Constructor

        Args:
            filename - path to zip file
            basepath
        """
        self.filename = filename
        self.basepath = basepath
        self.base_len = len(self.basepath)
        self.zip_file = zipfile.ZipFile(
            filename, "w", zipfile.ZIP_BZIP2, compresslevel=9
        )
        # self.zip_file = zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED, compresslevel=9)

        self.exclude = exclude
        if sha256:
            self.sha256_tab = []
        else:
            self.sha256_tab = None

    def close(self):
        self.zip_file.close()

    def _sha256_gen(self, file_name, data):
        if self.sha256_tab != None:
            sha256 = hashlib.sha256()
            sha256.update(data)
            self.sha256_tab.append((file_name, sha256.hexdigest(), len(data)))

    def write(self, file_name, name_in_zip=None, base_path_in_zip=None):
        test = True
        for pos in self.exclude:
            if re.match(pos, file_name, re.I) != None:
                test = False
                break
        if test:
            with open(file_name, "rb") as f:
                data = f.read()
                if name_in_zip:
                    self.writestr(name_in_zip, data)
                elif base_path_in_zip:
                    self.writestr(
                        base_path_in_zip + file_name[self.base_len + 1 :], data
                    )
                else:
                    self.writestr(file_name[self.base_len + 1 :], data)

    def writestr(self, path, data):
        self._sha256_gen(path, data)
        return self.zip_file.writestr(path, data)

    def to_zip(self, file, base_path_in_zip=None):
        if os.path.isfile(file):
            self.write(file, base_path_in_zip=base_path_in_zip)
        else:
            self.add_folder_to_zip(file, base_path_in_zip=base_path_in_zip)

    def add_folder_to_zip(self, folder, base_path_in_zip=None):
        for file in os.listdir(folder):
            full_path = os.path.join(folder, file)
            if os.path.isfile(full_path):
                self.write(full_path, base_path_in_zip=base_path_in_zip)
            elif os.path.isdir(full_path):
                self.add_folder_to_zip(full_path, base_path_in_zip=base_path_in_zip)


# Perhaps for delete
class Cmp(object):
    def __init__(self, masks, key, convert_to_re=False):
        if masks:
            self.masks = []
            for mask in masks:
                if convert_to_re:
                    x = (
                        mask[1:]
                        .replace(".", "\\.")
                        .replace("*", ".*")
                        .replace("?", ".")
                    )
                else:
                    x = mask[1:]
                self.masks.append((mask[0], re.compile(x)))
        else:
            self.masks = None
        if key:
            self.key = key.lower()
        else:
            self.key = None

    def re_cmp(self, value1, mask):
        ret = mask.match(value1)
        if ret:
            return True
        else:
            return False

    def masks_filter(self, file_name):
        if self.masks:
            sel = False
            for filter in self.masks:
                if filter[0] == "+":
                    if self.re_cmp(file_name, filter[1]):
                        sel = True
                else:
                    if self.re_cmp(file_name, filter[1]):
                        sel = False
            return sel
        else:
            return False

    def key_filter(self, file_name):
        if self.key:
            if file_name.lower().startswith(self.key):
                return True
            else:
                return False
            return True

    def filter(self, file_name):
        if self.key_filter(file_name) and self.masks_filter(file_name):
            return True
        return False


def automount(path):
    lpath = path.lower()
    if lpath.endswith(".zip") or ".zip/" in lpath:
        id = lpath.find(".zip")
        pp = path[: id + 4]

        syspath = default_storage.fs.getsyspath(pp, allow_none=True)
        if syspath:
            zip_name = "zip://" + default_storage.fs.getsyspath(pp)
            # default_storage.fs.mountdir(pp[1:], fsopendir(zip_name))
            default_storage.fs.add_fs(pp[1:], OSFS(zip_name))
    return path


# input formats: ihtml, html, imd, md, spdf
# output formats: html, spdf, pdf, xpdf, xlsx, docx
# xpdf - pdf with source text in subject field
# spdf - recorded BaseDc operation to zip file format renamed to spdf


def convert_file(
    filename_or_stream_in,
    filename_or_stream_out,
    input_format=None,
    output_format=None,
    for_vfs_input=True,
    for_vfs_output=True,
):

    from pytigon_lib.schhtml.basedc import BaseDc
    from pytigon_lib.schhtml.pdfdc import PdfDc
    from pytigon_lib.schhtml.cairodc import CairoDc
    from pytigon_lib.schhtml.docxdc import DocxDc
    from pytigon_lib.schhtml.xlsxdc import XlsxDc
    from pytigon_lib.schhtml.htmlviewer import HtmlViewerParser
    from pytigon_lib.schindent.indent_style import ihtml_to_html_base
    from pytigon_lib.schindent.indent_markdown import markdown_to_html
    from pytigon_lib.schfs import open_file

    from pytigon_lib.schindent.indent_markdown import (
        IndentMarkdownProcessor,
        REG_OBJ_RENDERER,
    )

    i_f = input_format
    o_f = output_format
    if type(filename_or_stream_in) == str:
        if for_vfs_input:
            fin = default_storage.fs.open(automount(filename_or_stream_in), "rt")
        else:
            fin = open(filename_or_stream_in, "rb")
        if not i_f:
            i_f = filename_or_stream_in.split(".")[-1].lower()
    else:
        fin = filename_or_stream_in

    if type(filename_or_stream_out) == str:
        if for_vfs_output:
            fout = default_storage.fs.open(automount(filename_or_stream_out), "wb")
        else:
            fout = open(filename_or_stream_out, "wb")
        if not o_f:
            o_f = filename_or_stream_out.split(".")[-1].lower()
    else:
        fout = filename_or_stream_out

    if i_f == "imd":
        x = IndentMarkdownProcessor(output_format="html")
        buf = x.convert(fin.read())
    elif i_f == "md":
        buf = markdown_to_html(fin.read())
    elif i_f == "ihtml":
        buf = ihtml_to_html_base(None, input_str=fin.read())
    elif i_f == "spdf":
        buf = None
    else:
        buf = fin.read()
    if o_f == "html":
        fout.write(buf.encode("utf-8"))
        return True

    if o_f in ("pdf", "xpdf"):

        def notify_callback(event_name, data):
            if event_name == "end":
                dc = data["dc"]
                dc.surf.pdf.set_subject(buf)

        if o_f == "xpdf":
            dc = PdfDc(output_stream=fout, notify_callback=notify_callback)
        else:
            dc = PdfDc(output_stream=fout)
        dc.set_paging(True)
    elif o_f == "spdf":

        def notify_callback(event_name, data):
            if event_name == "end":
                print("SAVE:")
                dc = data["dc"]
                if dc.output_name:
                    dc.save(dc.output_name)
                else:
                    result_buf = NamedTemporaryFile(delete=False)
                    spdf_name = result_buf.name
                    result_buf.close()

                    dc.save(spdf_name)

                    with open(spdf_name, "rb") as f:
                        dc.output_stream.write(f.read())

        (width, height) = (595, 842)
        dc = PdfDc(
            output_stream=fout,
            calc_only=True,
            width=width,
            height=height,
            notify_callback=notify_callback,
            record=True,
        )
        dc.set_paging(True)
    elif o_f == "docx":
        dc = DocxDc(
            output_stream=fout,
        )
    elif o_f == "xlsx":
        dc = XlsxDc(output_stream=fout)

    p = HtmlViewerParser(
        dc=dc, calc_only=False, init_css_str="@wiki.icss", css_type=1, use_tag_maps=True
    )
    if i_f == "spdf":
        dc.load(filename_or_stream_in)
        dc.play()
    else:
        p.feed(buf)
    p.close()

    if type(filename_or_stream_in) == str:
        if fin:
            fin.close()
    if type(filename_or_stream_out) == str:
        if fout:
            fout.close()
    return True
