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
# for more details.

# Pytigon - wxpython and django application framework

# author: "Slawomir Cholaj (slawomir.cholaj@gmail.com)"
# copyright: "Copyright (C) ????/2012 Slawomir Cholaj"
# license: "LGPL 3.0"
# version: "0.1a"

"""Module contain class and functions for odf file transformations.

"""

from xml.dom.expatbuilder import TEXT_NODE
from zipfile import ZipFile, ZIP_DEFLATED
import re
import shutil

try:
    from lxml import etree
except:
    pass
import base64

from pytigon_lib.schfs.vfstools import delete_from_zip

OFFICE_URN = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"
TABLE_URN = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
TEXT_URN = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"


def attr_get(attrs, key):
    for k in attrs.keys():
        if k.endswith(key):
            return attrs[k]
    return None


def transform_str(s):
    return s.replace("***", '"').replace("**", "'")


class OdfDocTransform:
    """Transformate odf file"""

    def __init__(self, file_name_in, file_name_out=None):
        """Constructor

        Args:
            file_name_in - input file name
            file_name_out - output file name - if none output file name is composed from input file name.
        """
        self.file_name_in = file_name_in
        if file_name_out == None:
            self.file_name_out = file_name_in.replace("_", "")
        else:
            self.file_name_out = file_name_out
        self.process_tables = None
        self.doc_type = 1
        self.buf = None

    def set_doc_type(self, doc_type):
        """
        doc_type:
            0 - other
            1 - spreadsheet
            2 - writer
        """
        self.doc_type = doc_type

    def set_process_tables(self, tables):
        self.process_tables = tables

    def nr_col(self):
        return """{{ tbl.IncCol }}"""

    def nr_row(self, il=1):
        return """{{ tbl|args:%d|call:'IncRow' }}{{ tbl|args:1|call:'SetCol' }}""" % il

    def zer_row_col(self):
        return """{{ tbl|args:1|call:'SetRow' }}{{ tbl|args:1|call:'SetCol' }}"""

    def doc_process(self, doc, debug):
        pass

    def spreadsheet_process(self, doc, debug):
        elementy = doc.findall(".//{*}p")
        for element in elementy:
            if element.getparent().tag.endswith("annotation"):
                data = ""
                for child in element:
                    if child.text:
                        data += child.text

                if data != "" and "!" in data:
                    data = data[data.find("!") :]
                    poziom = 1
                    if len(data) > 1 and data[1] == "!":
                        if len(data) > 2 and data[2] == "*":
                            poziom = 3
                        else:
                            poziom = 2
                    if "@" in data[poziom:]:
                        skladniki = data[poziom:].split("@")
                    else:
                        skladniki = data[poziom:].split("$")
                    x = element.getparent()
                    y = element.getparent().getparent()
                    y.remove(x)
                    if poziom > 1:
                        y = y.getparent()
                    if poziom > 2:
                        y = y.getparent()
                    new_cell = etree.Element("tmp")
                    parent = y.getparent()
                    parent[parent.index(y)] = new_cell
                    new_cell.text = skladniki[0]
                    new_cell.append(y)
                    if len(skladniki) > 1:
                        if new_cell.tail:
                            new_cell.tail += skladniki[1]
                        else:
                            new_cell.tail = skladniki[1]

        elementy = doc.findall(".//{*}table-cell")
        for element in elementy:
            nr = attr_get(element.attrib, "number-columns-repeated")
            if nr:
                nr = int(nr)
                if nr > 1000:
                    element.set(TABLE_URN + "number-columns-repeated", "1000")

            if attr_get(element.attrib, "value-type") == "string":
                txt = etree.tostring(element, method="text", encoding="utf-8").decode(
                    "utf-8"
                )
                test = False
                for item in (":=", ":*", ":*", "{{", "}}", "{%", "%}"):
                    if item in txt:
                        test = True
                if test:
                    txt = transform_str(txt.strip())
                    if txt.startswith(":="):
                        new_cell = etree.Element(TABLE_URN + "table-cell")
                        new_cell.set(OFFICE_URN + "value-type", "float")
                        new_cell.set(OFFICE_URN + "value", "0")
                        new_cell.set(TABLE_URN + "formula", "of:=" + txt[2:])
                        new_text = etree.Element(OFFICE_URN + "p")
                        new_cell.append(new_text)
                        if debug:
                            new_annotate = etree.Element(OFFICE_URN + "annotation")
                            new_text_a = etree.Element(TEXT_URN + "p")
                            new_text_a.text = txt[2:].replace("^", "")
                            new_annotate.append(new_text_a)
                            new_cell.append(new_annotate)
                        style = attr_get(element.attrib, "style-name")
                        if style:
                            new_cell.set(TABLE_URN + "style-name", style)
                        new_cell2 = etree.Element("tmp")
                        new_cell2.append(new_cell)
                        new_cell2.text = self.nr_col()
                        parent = element.getparent()
                        parent[parent.index(element)] = new_cell2
                    else:
                        new_cell = etree.Element(TABLE_URN + "table-cell")
                        if txt.startswith(":0"):
                            new_cell.set(OFFICE_URN + "value-type", "float")
                            new_cell.set(OFFICE_URN + "value", str(txt[2:]))
                            new_text = etree.Element(TEXT_URN + "p")
                            new_text.text = str(txt[2:])
                            new_cell.append(new_text)
                        else:
                            new_cell.set(OFFICE_URN + "value-type", "string")
                            new_text = etree.Element(TEXT_URN + "p")
                            if txt.startswith(":*"):
                                new_text.text = txt[2:]
                            else:
                                new_text.text = txt
                            new_cell.append(new_text)
                        if debug:
                            new_annotate = etree.Element(OFFICE_URN + "annotation")
                            new_text_a = etree.Element(TEXT_URN + "p")
                            if txt.startswith(":*"):
                                new_text_a.text = txt[2:]
                            else:
                                new_text_a.text = txt
                            new_annotate.append(new_text_a)
                            new_cell.append(new_annotate)
                        style_name = attr_get(element.attrib, "style-name")
                        if style_name:
                            new_cell.set(TABLE_URN + "style-name", style_name)
                        new_cell2 = etree.Element("tmp")
                        new_cell2.append(new_cell)
                        new_cell2.text = self.nr_col()

                        parent = element.getparent()
                        parent[parent.index(element)] = new_cell2

        elementy = doc.findall(".//{*}table-row")
        for element in elementy:
            parent = element.getparent()
            new_cell = etree.Element("tmp")
            nr = attr_get(element.attrib, "number-rows-repeated")
            if nr:
                nr = int(nr)
                if nr > 1000:
                    element.set(TABLE_URN + "number-rows-repeated", "1000")
            else:
                nr = 1

            parent = element.getparent()
            parent[parent.index(element)] = new_cell

            new_cell.append(element)
            new_cell.text = self.nr_row(nr)

        elementy = doc.findall(".//{*}table")
        for element in elementy:
            parent = element.getparent()
            new_cell = etree.Element("tmp")
            new_cell.text = self.zer_row_col()
            parent[parent.index(element)] = new_cell
            new_cell.append(element)

        if self.process_tables != None:
            elementy = doc.findall(".//{*}table")
            for element in elementy:
                if not attr_get(element.attrib, "name") in self.process_tables:
                    new_cell = etree.Element("tmp")
                    parent = element.getparent()
                    parent[parent.index(element)] = new_cell

    def process_template(self, doc_str, context):
        pass

    def extended_transformation(self, xml_name, script):
        xml = etree.fromstring(self.buf.encode("utf-8"))
        script(self, xml)
        self.buf = etree.tostring(xml, encoding="utf-8", xml_declaration=True).decode(
            "utf-8"
        )

    def process(self, context, debug):
        """Transform input file

        Args:
            context - python dict with variables used for transformation
            debut - print debug information
        """
        shutil.copyfile(self.file_name_in, self.file_name_out)
        z = ZipFile(self.file_name_out, "r")
        doc_content = z.read("content.xml").decode("utf-8")
        z.close()

        if (
            delete_from_zip(
                self.file_name_out,
                [
                    "content.xml",
                ],
            )
            == 0
        ):
            return

        doc = etree.fromstring(
            doc_content.replace("&apos;", "'")
            .replace("_start_", "{{")
            .replace("_end_", "}}")
            .encode("utf-8")
        )

        if self.doc_type == 1:
            self.spreadsheet_process(doc, debug)
        if self.doc_type == 2:
            self.doc_process(doc, debug)

        doc_str = (
            etree.tostring(doc, encoding="utf-8", xml_declaration=True)
            .decode("utf-8")
            .replace("<tmp>", "")
            .replace("</tmp>", "")
        )

        p = re.compile("\^(.*?\(.*?\))")
        doc_str = p.sub(r"${\1}", doc_str)

        if "expr_escape" in context:
            doc_str = doc_str.replace("{{", "{% expr_escape ").replace("}}", " %}")

        x = self.process_template(doc_str, context)
        if not x:
            x = doc_str

        files = []
        if "[[[" in x and "]]]" in x:
            data = [pos.split("]]]")[0] for pos in x.split("[[[")[1:]]
            data2 = [pos.split("]]]")[-1] for pos in x.split("[[[")]
            fdata = []
            i = 1
            for pos in data:
                x = pos.split(",", 1)
                ext = x[0].split(";")[0].split("/")[-1]
                name = "Pictures/pytigon_%d.%s" % (i, ext)
                fdata.append(name)
                files.append([name, x, ext])
                i += 1

            data3 = [None] * (len(data) + len(data2))
            data3[::2] = data2
            data3[1::2] = fdata
            x = "".join(data3)

        self.buf = x

        if "extended_transformations" in context:
            for pos in context["extended_transformations"]:
                self.extended_transformation(pos[0], pos[1])

        z = ZipFile(self.file_name_out, "a", ZIP_DEFLATED)
        z.writestr("content.xml", self.buf.encode("utf-8"))

        for pos in files:
            z.writestr(pos[0], base64.b64decode(pos[1].encode("utf-8")))

        z.close()

        return 1


if __name__ == "__main__":
    x = OdfDocTransform("./test.ods", "./test_out.ods")
    object_list = ["x1", "x2", "x3"]
    context = {"test": 1, "object_list": object_list}
    x.process(context, False)
