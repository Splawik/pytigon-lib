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

from zipfile import ZipFile, ZIP_DEFLATED
import re
import shutil
try:
    from lxml import etree
except:
    pass
import base64

from pytigon_lib.schfs.vfstools import delete_from_zip


def attr_get(attrs, key):
    for k in attrs.keys():
        if k.endswith(key):
            return attrs[k]
    return None


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
        # return """{{ tbl.IncCol()}}"""
        return """{{ tbl.IncCol }}"""

    def nr_row(self, il=1):
        # return """{{ tbl.IncRow(%d)}}{{ tbl.SetCol(1) }}""" % il
        return """{{ tbl|args:%d|call:'IncRow' }}{{ tbl|args:1|call:'SetCol' }}""" % il

    def zer_row_col(self):
        # return """{{ tbl.SetRow(1) }}{{ tbl.SetCol(1) }}"""
        return """{{ tbl|args:1|call:'SetRow' }}{{ tbl|args:1|call:'SetCol' }}"""

    def doc_process(self, doc, debug):
        pass

    def spreadsheet_process(self, doc, debug):
        elementy = doc.findall(".//{*}p")
        for element in elementy:
            print("A1")
            print(element.getparent().tag)
            if element.getparent().tag.endswith("annotation"):
                data = ""
                for child in element:
                    if hasattr(child, "text"):
                        data += child.text

                if data != "" and "!" in data:
                    data = data[data.find("!") :]
                    poziom = 1
                    if len(data) > 1 and data[1] == "!":
                        if len(data) > 2 and data[2] == "!":
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
                    if new_cell.text:
                        new_cell.text += skladniki[0]
                    else:
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
                    element.set("number-columns-repeated", "1000")

            if attr_get(element.attrib, "value-type") == "string":
                for child in element:
                    if child and len(child) > 0 and hasattr(child[0], "data"):
                        if (
                            child[0].text
                            and len(child[0].text) > 0
                            and (
                                child[0].text[0] == "*"
                                or child[0].text[0] == ":"
                                or child[0].text[0] == "@"
                                or child[0].text[0] == "$"
                            )
                        ):
                            if child[0].text[0] == ":" or child[0].text[0] == "*":
                                new_cell = etree.Element("table:table-cell")
                                if child[0].text[0] == ":":
                                    new_cell.set("office:value-type", "float")
                                    new_cell.set("office:value", str(child[0].text[1:]))
                                    new_text = etree.Element("text:p")
                                else:
                                    new_cell.set("office:value-type", "string")
                                    new_text = etree.Element("text:p")
                                    new_text.text += str(child[0].text[1:])
                                if debug:
                                    new_annotate = etree.Element("office:annotation")
                                    new_text_a = etree.Element("text:p")
                                    new_text_a.text += child[0].text[2:-1]
                                    new_annotate.append(new_text_a)
                                new_cell.append(new_text)
                                if debug:
                                    new_cell.append(new_annotate)
                                new_cell.set(
                                    "table:style-name",
                                    attr_get(element.attrib, "style-name"),
                                )
                                new_cell2 = etree.Element("tmp")
                                new_cell2.append(new_cell)
                                new_cell2.text += self.nr_col()

                                parent = element.getparent()
                                parent[parent.index(element)] = new_cell2

                            if child[0].text[0] == "@" or child[0].text[0] == "$":
                                new_cell = etree.Element("table:table-cell")
                                new_cell.set("office:value-type", "float")
                                new_cell.set("office:value", "0")
                                if child[0].text[0] == "@":
                                    new_cell.set(
                                        "table:formula",
                                        "oooc:=" + child[0].text[1:],
                                    )
                                else:
                                    new_cell.set(
                                        "table:formula",
                                        "msoxl:=" + child[0].text[1:],
                                    )
                                new_text = etree.Element("text:p")
                                if debug:
                                    new_annotate = etree.Element("office:annotation")
                                    new_text_a = etree.Element("text:p")
                                    new_text_a.text += (
                                        child[0].text[1:].replace("^", "")
                                    )
                                    new_annotate.append(new_text_a)
                                new_cell.append(new_text)
                                if debug:
                                    new_cell.append(new_annotate)
                                new_cell.set(
                                    "table:style-name",
                                    attr_get(element.attrib, "style-name"),
                                )
                                new_cell2 = etree.Element("tmp")
                                new_cell2.append(new_cell)
                                new_cell2.text += self.nr_col()

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
                    element.set("number-rows-repeated", "1000")
            else:
                nr = 1

            parent = element.getparent()
            parent[parent.index(element)] = new_cell

            new_cell.append(element)
            new_cell.text = self.nr_row(nr)

        elementy = doc.findall(".//{*}table:table")
        for element in elementy:
            parent = element.getparent()
            new_cell = etree.Element("tmp")
            new_cell.text += self.zer_row_col()
            parent[parent.index(element)] = new_cell
            new_cell.append(element)

        if self.process_tables != None:
            elementy = doc.findall(".//{*}table:table")
            for element in elementy:
                if not attr_get(element.attrib, "name") in self.process_tables:
                    new_cell = etree.Element("tmp")
                    parent = element.getparent()
                    parent[parent.index(element)] = new_cell

    def process_template(self, doc_str, context):
        pass

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
            etree.tostring(doc)
            .decode("utf-8")
            .replace("<tmp>", "")
            .replace("</tmp>", "")
        )

        p = re.compile("\^(.*?\(.*?\))")
        doc_str = p.sub(r"${\1}", doc_str)
        
        if 'expr_escape' in context:
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

        z = ZipFile(self.file_name_out, "a", ZIP_DEFLATED)
        z.writestr("content.xml", x.encode("utf-8"))

        for pos in files:
            z.writestr(pos[0], base64.b64decode(pos[1].encode("utf-8")))

        z.close()

        return 1


if __name__ == "__main__":
    x = OdfDocTransform("./test.ods", "./test_out.ods")
    object_list = ["x1", "x2", "x3"]
    context = {"test": 1, "object_list": object_list}
    x.process(context, False)
