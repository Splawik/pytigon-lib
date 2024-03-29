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
# copyright: "Copyright (C) ????/2019 Slawomir Cholaj"
# license: "LGPL 3.0"
# version: "0.1a"

"""Module contain class and functions for xlsx file transformations.

"""

import zipfile
import shutil
import os
import sys
import datetime

import dateutil.parser

try:
    from lxml import etree
    from xml.sax.saxutils import escape
except:
    pass
import email.generator

from django.template import Context
from django.template import Template

from pytigon_lib.schspreadsheet.odf_process import OdfDocTransform
from pytigon_lib.schfs.vfstools import delete_from_zip

SECTION_WIDTH = ord("Z") - ord("A") + 1


def transform_str(s):
    return s.replace("***", '"').replace("**", "'")


def filter_attr(tab, attr, value):
    check_type = 0
    ret = []
    if value.startswith("*"):
        check_type = 1
    if value.endswith("*"):
        if check_type == 1:
            check_type = 3
        else:
            check_type = 2

    for pos in tab:
        if attr in pos.attrib:
            if check_type == 0 and pos.attrib[attr] == value:
                ret.append(pos)
            elif check_type == 1 and pos.attrib[attr].endswith(value[1:]):
                ret.append(pos)
            elif check_type == 2 and pos.attrib[attr].startswith(value[:-1]):
                ret.append(pos)
            elif check_type == 3 and value[1:-1] in pos.attrib[attr]:
                ret.append(pos)
    return ret


def col_row(excel_addr):
    if excel_addr[1] >= "0" and excel_addr[1] <= "9":
        col = excel_addr[0].upper()
        row = int(excel_addr[1:])
    else:
        col = excel_addr[:2].upper()
        row = int(excel_addr[2:])

    if len(col) > 1:
        col_as_int = (
            (ord(col[0]) - ord("A") + 1) * SECTION_WIDTH + (ord(col[1]) - ord("A")) + 1
        )
    else:
        col_as_int = ord(col[0]) - ord("A") + 1

    return col, row, col_as_int


def make_col_row(col, row):
    _col, _row, col_as_int = col_row("Z1")
    if col > col_as_int:
        x1 = (col - 1) // col_as_int
        x2 = (col - 1) % col_as_int
        return chr(ord("A") + x1 - 1) + chr(ord("A") + x2) + str(row)
    else:
        return chr(ord("A") + col - 1) + str(row)


def key_for_addr(excel_addr):
    col, row, col_as_int = col_row(excel_addr)
    return row * 1000 + col_as_int


def date_to_float(d):
    dt = d - datetime.datetime(1899, 12, 30)
    return dt.days + dt.seconds / 86400


class OOXmlDocTransform(OdfDocTransform):
    """Transformate odf file"""

    def __init__(self, file_name_in, file_name_out=None):
        """Constructor

        Args:
            file_name_in - input file name
            file_name_out - output file name - if none output file name is composed from input file name.
        """
        super().__init__(file_name_in, file_name_out)

        self.file_name_in = file_name_in
        if file_name_out == None:
            self.file_name_out = file_name_in.replace("_", "")
        else:
            self.file_name_out = file_name_out

        self.zip_file = None
        self.to_update = None
        self.shared_strings = {}
        self.comments = {}

    def doc_process(self, doc, debug):
        pass

    def get_xml_content(self, xml_name):
        xml = None
        for pos in self.to_update:
            if xml_name == pos[0]:
                xml = pos[1]
                break
        if xml:
            return {"data": xml, "from_cache": True}

        content = self.zip_file.read(xml_name)
        return {"data": etree.XML(content), "from_cache": False}

    def extended_transformation(self, xml_name, script):
        ret = self.get_xml_content(xml_name)
        xml = ret["data"]
        ret2 = script(self, xml)
        if ret2 and not ret["from_cache"]:
            self.to_update.append((xml_name, xml))

        # xml = None
        # for pos in self.to_update:
        #    if xml_name == pos[0]:
        #        xml = pos[1]
        #        break
        # if xml:
        #    script(self, xml)
        # else:
        #    content = self.zip_file.read(xml_name)
        #    root = etree.XML(content)
        #    if script(self, root):
        #        self.to_update.append((xml_name, root))

    def add_comments(self, sheet):

        if self.comments:
            labels = []
            d = sheet.findall(".//c", namespaces=sheet.nsmap)
            for pos in d:
                if "r" in pos.attrib:
                    labels.append(pos.attrib["r"])
            labels.sort(key=key_for_addr)

            for key, value in self.comments.items():
                key2 = key.upper()
                value2 = value.strip()
                after = 0
                if key in labels:
                    label = key
                else:
                    labels2 = labels + [
                        key,
                    ]
                    labels2.sort(key=key_for_addr)
                    old = None
                    for l in labels2:
                        if l == key:
                            break
                        old = l
                    if old:
                        label = old
                        after = 1
                    else:
                        label = labels[0]

                d = filter_attr(
                    sheet.findall(".//c", namespaces=sheet.nsmap), "r", label
                )
                if len(d) > 0:
                    parent = d[0].getparent()
                    if "@" in value2:
                        x = value2.split("@")
                        values = [x[0], x[1]]
                        if not x[0].startswith("^") and not x[1].startswith("$"):
                            values[0] = "^" + values[0]
                            values[1] = "$" + values[1]
                    else:
                        values = [value2]
                    for v in values:
                        if v.startswith("^") or v.startswith("!!"):
                            if v.startswith("!!"):
                                value3 = v[2:]
                            else:
                                value3 = v[1:]
                            gparent = parent.getparent()
                            gparent.insert(
                                gparent.index(parent),
                                etree.XML("<tmp>%s</tmp>" % escape(value3)),
                            )
                        elif v.startswith("$"):
                            value3 = v[1:]
                            gparent = parent.getparent()
                            gparent.insert(
                                gparent.index(parent) + 1,
                                etree.XML("<tmp>%s</tmp>" % escape(value3)),
                            )
                        elif v.startswith("!"):
                            parent.insert(
                                parent.index(d[0]) + after,
                                etree.XML("<tmp>%s</tmp>" % escape(v[1:])),
                            )
                        else:
                            parent.insert(
                                parent.index(d[0]) + after,
                                etree.XML("<tmp>%s</tmp>" % escape(v)),
                            )

    def shared_strings_to_inline(self, sheet):
        d = filter_attr(sheet.findall(".//c", namespaces=sheet.nsmap), "t", "s")
        for pos in d:
            v = pos.find(".//v", namespaces=sheet.nsmap)
            try:
                id = int(v.text)
            except:
                id = -1
            if id >= 0:
                s = self.shared_strings[id]
                if s:
                    if s.startswith(":="):
                        pos.remove(v)
                        pos.attrib["t"] = ""
                        pos.append(etree.XML("<f>%s</f>" % escape(s[2:])))
                    elif s.startswith(":?"):
                        pos.remove(v)
                        pos.attrib["t"] = ""
                        pos.append(etree.XML("<vauto>%s</vauto>" % escape(s[2:])))
                    elif s.startswith(":0"):
                        pos.remove(v)
                        pos.attrib["t"] = "n"
                        pos.append(etree.XML("<v>%s</v>" % escape(s[2:])))
                    elif s.startswith(":*"):
                        pos.attrib["t"] = "inlineStr"
                        pos.remove(v)
                        pos.append(etree.XML("<is><t>%s</t></is>" % escape(s[2:])))
                    elif ("{{" in s and "}}" in s) or ("{%" in s and "%}" in s):
                        pos.attrib["t"] = "inlineStr"
                        pos.remove(v)
                        pos.append(etree.XML("<is><t>%s</t></is>" % escape(s)))

    def process_template(self, doc_str, context):
        pass

    # def transform_template(self, template_str, context):
    #    template_header = "{% load exfiltry %}{% load exsyntax %}{% load expr %}"
    #    template = Template(template_header + template_str)
    #    return template.render(context)

    def repair_xml(self, sheet):
        max_row = 0
        max_col = 0
        d = sheet.findall(".//row", namespaces=sheet.nsmap)
        i = 1
        for row in d:
            if "r" in row.attrib:
                i2 = int(row.attrib["r"])
                if i2 < i:
                    row.attrib["r"] = str(i)
                elif i2 > i:
                    i = i2
            d2 = row.findall(".//c", namespaces=sheet.nsmap)
            j = 1
            for c in d2:
                if "r" in c.attrib:
                    a = c.attrib["r"]
                    _c, _r, c_id = col_row(a)
                    if _r != i or c_id != j:
                        if c_id < j:
                            c_id = j
                        else:
                            j = c_id
                        c.attrib["r"] = make_col_row(c_id, i)
                j += 1
                if j > max_col:
                    max_col = j
            i += 1

        max_row = i - 1
        max_col = max_col - 1
        max_addr = make_col_row(max_col, max_row)

        if max_row > 0 and max_col > 0:
            d = sheet.find(".//dimension", namespaces=sheet.nsmap)
            if d != None:
                if "ref" in d.attrib:
                    addr = d.attrib["ref"]
                    d.attrib["ref"] = "A1:" + max_addr

        auto_list = sheet.findall(".//vauto", namespaces=sheet.nsmap)
        for pos in auto_list:
            parent = pos.getparent()
            txt = pos.text
            parent.remove(pos)
            if txt != "" and txt != None:
                if (
                    (len(txt) == 10 or len(txt) == 19)
                    and txt[4] == "-"
                    and txt[7] == "-"
                ):
                    try:
                        d = dateutil.parser.parse(txt)
                        x = date_to_float(d)
                        parent.append(etree.XML("<v>%f</v>" % x))
                        continue
                    except:
                        pass
                try:
                    x = float(txt)
                    parent.append(etree.XML("<v>%s</v>" % escape(txt)))
                    continue
                except:
                    pass

            parent.attrib["t"] = "inlineStr"
            try:
                if txt:
                    parent.append(etree.XML("<is><t>%s</t></is>" % escape(txt)))
                else:
                    parent.append(etree.XML("<is><t></t></is>"))
            except:
                print(txt)

        c_list = sheet.findall(".//c", namespaces=sheet.nsmap)
        for pos in c_list:
            f = pos.find(".//f", namespaces=sheet.nsmap)
            if f != None:
                v = pos.find(".//v", namespaces=sheet.nsmap)
                if v != None:
                    pos.remove(v)

    def handle_sheet(self, sheet, django_context):
        self.shared_strings_to_inline(sheet)
        self.add_comments(sheet)
        sheet_str = etree.tostring(sheet, pretty_print=True).decode("utf-8")
        sheet_str = self.process_template(sheet_str, django_context)
        root = etree.XML(sheet_str)
        self.repair_xml(root)
        return root

    def process(self, context, debug):
        """Transform input file

        Args:
            context - python dict with variables used for transformation
            debut - print debug information

        """
        django_context = Context(context)
        if "doc_type" in context and context["doc_type"] != "xlsx":
            xlsx = False
        else:
            xlsx = True
        shutil.copyfile(self.file_name_in, self.file_name_out)
        self.to_update = []
        self.zip_file = zipfile.ZipFile(self.file_name_out, "r")
        if xlsx:
            try:
                shared_strings_str = self.zip_file.read("xl/sharedStrings.xml")
                root = etree.XML(shared_strings_str)
                d2 = root.findall(".//si", namespaces=root.nsmap)
                self.shared_strings = [
                    transform_str(
                        etree.tostring(pos, method="text", encoding="utf-8").decode(
                            "utf-8"
                        )
                    )
                    for pos in d2
                ]
            except:
                # no shared strings
                self.shared_strings = []
            id = 1
            while True:
                if (
                    "no_process_sheets" in context
                    and id in context["no_process_sheets"]
                ):
                    id += 1
                    continue
                try:
                    sheet_name = "xl/worksheets/sheet%d.xml" % id
                    sheet_str = self.zip_file.read(sheet_name)
                    sheet = etree.XML(sheet_str)
                    self.comments = {}
                    try:
                        sheet_rels_name = "xl/worksheets/_rels/sheet%d.xml.rels" % id
                        sheet_rels_str = self.zip_file.read(sheet_rels_name)
                        root = etree.XML(sheet_rels_str)
                        d1 = root.findall(".//{*}Relationship", namespaces=root.nsmap)
                        d2 = filter_attr(
                            d1,
                            "Type",
                            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments",
                        )
                        if len(d2) > 0:
                            comments_name = os.path.normpath(
                                "xl/worksheets/" + d2[0].attrib["Target"]
                            ).replace("\\", "/")
                            comments_str = self.zip_file.read(comments_name)
                            root = etree.XML(comments_str)
                            d1 = root.findall(".//{*}comment", namespaces=root.nsmap)
                            for pos in d1:
                                ref = pos.attrib["ref"]
                                d2 = pos.findall(
                                    ".//{*}text/{*}r/{*}t", namespaces=root.nsmap
                                )
                                for pos2 in d2:
                                    if "{{" in pos2.text or "{%" in pos2.text:
                                        self.comments[ref] = pos2.text
                                        comment = (
                                            pos2.getparent().getparent().getparent()
                                        )
                                        comment_list = comment.getparent()
                                        comment_list.remove(comment)
                            self.to_update.append((comments_name, root))
                    except KeyError:
                        pass

                    sheet2 = self.handle_sheet(sheet, django_context)
                    self.to_update.append((sheet_name, sheet2))
                except KeyError:
                    break
                id += 1
            if "extended_transformations" in django_context:
                for pos in django_context["extended_transformations"]:
                    self.extended_transformation(pos[0], pos[1])

            self.zip_file.close()
            delete_from_zip(self.file_name_out, [pos[0] for pos in self.to_update])
            z = zipfile.ZipFile(self.file_name_out, "a", zipfile.ZIP_DEFLATED)
            for pos in self.to_update:
                z.writestr(
                    pos[0],
                    etree.tostring(pos[1], pretty_print=True)
                    .decode("utf-8")
                    .replace("<tmp>", "")
                    .replace("</tmp>", ""),
                )
            z.close()
        else:
            doc_type = context["doc_type"]
            if doc_type == "docx":
                doc_name = "word/document.xml"
                doc_str = self.zip_file.read(doc_name).decode("utf-8")
                doc_str = self.process_template(doc_str, django_context)
                self.to_update.append(doc_name, doc_str)
            elif doc_type == "pptx":
                id = 1
                while True:
                    doc_name = "ppt/slides/slide%d.xml" % id
                    try:
                        doc_str = self.zip_file.read(doc_name).decode("utf-8")
                        doc_str2 = self.process_template(doc_str, django_context)
                        if doc_str != doc_str2:
                            self.to_update.append((doc_name, doc_str2))
                        id += 1
                    except KeyError:
                        break
            else:
                return 0
            self.zip_file.close()
            if self.to_update:
                delete_from_zip(
                    self.file_name_out,
                    [item[0] for item in self.to_update],
                )
                z = zipfile.ZipFile(self.file_name_out, "a", zipfile.ZIP_DEFLATED)
                for item in self.to_update:
                    z.writestr(item[0], item[1].encode("utf-8"))
                z.close()

        return 1


if __name__ == "__main__":
    from django.conf import settings
    import django

    settings.configure(
        TEMPLATES=[
            {
                "BACKEND": "django.template.backends.django.DjangoTemplates",
            }
        ]
    )
    django.setup()

    x = OOXmlDocTransform("./in.xlsx", "./test_out.xlsx")
    context = {"test": 1}
    x.process(context, False)
