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

import io
from pytigon_lib.schhtml.parser import Parser


def _convert_strings(lines):
    line_buf = None
    in_string = False
    lines.seek(0)
    for line2 in lines:
        line = line2.replace("\n", "")
        id = line.find('"""')
        if in_string:
            if id >= 0:
                yield line_buf + "\n" + line.replace("\n", "")
                line_buf = None
                in_string = False
            else:
                if line_buf:
                    line_buf = line_buf + line.replace("\n", "")
                else:
                    line_buf = line.replace("\n", "")
        else:
            if id >= 0:
                id2 = line[id:].find('"""')
                if id2 >= 0:
                    if line_buf:
                        yield line_buf + line.replace("\n", "")
                        line_buf = None
                    else:
                        yield line.replace("\n", "")
                else:
                    in_string = True
                    if line_buf:
                        line_buf = line_buf + "\n" + line.replace("\n", "")
                    else:
                        line_buf = line.replace("\n", "")
            else:
                yield line.replace("\n", "")
                line_buf = None


def spaces_count(s):
    il = 0
    for znak in s:
        if znak == " ":
            il += 1
        else:
            return il
    return il


def norm_tab(f):
    old_il = 0
    poziom = 0
    tabpoziom = [0]
    tabkod = []
    for l in _convert_strings(f):
        line = l.replace("\t", "        ").replace("\n", "").rstrip()
        if line.lstrip() == "":
            continue
        il = spaces_count(line)
        if il > old_il:
            poziom += 1
            tabpoziom.append(il)
        else:
            if il < old_il:
                while il < tabpoziom[-1]:
                    poziom -= 1
                    del tabpoziom[-1]
        if len(line[il:]) > 0:
            tabkod.append((poziom, line[il:]))
        old_il = il
    return tabkod


def reformat_js(tabkod):
    tabkod2 = []
    sep = ""
    for pos in tabkod:
        code = pos[1]
        postfix = ""
        if code[:4] == "def " and code[-1] == ":":
            code = "function " + code[4:]
        if code.endswith("({"):
            postfix = "})"
            code = code[:-2] + "({"
            sep = ","
        elif code.endswith("("):
            postfix = ")"
            code = code[:-1] + "("
            sep = ","
        elif code.endswith("["):
            postfix = "]"
            code = code[:-1] + "["
            sep = ","
        elif code.endswith("[,"):
            postfix = "],"
            code = code[:-2] + "["
            sep = ","
        elif code.endswith(":"):
            postfix = "}"
            sep = ";"
            code = code[:-1] + "{"
        elif code.endswith("/:"):
            postfix = ""
            sep = ""
            code = code[:-2]
        elif code.endswith("="):
            postfix = "}"
            code = code[:-1] + "= {"
            sep = ","
        elif code.endswith("{"):
            postfix = "}"
            code = code[:-1] + "{"
            sep = ","
        tabkod2.append((pos[0], code, postfix, sep))

    tabkod2.append([0, "", "", ""])
    tabkod3 = []
    stack = []

    for pos in tabkod2:
        while len(stack) > 0:
            if pos[0] > stack[-1][0]:
                stack.append(pos)
                break
            top = stack.pop()
            if pos[0] == top[0]:
                if len(stack) > 0:
                    x = stack[-1][3]
                else:
                    x = ";"
                tabkod3[-1][1] += x
            else:
                if len(stack) > 0:
                    tabkod3.append([stack[-1][0], stack[-1][2]])
        tabkod3.append([pos[0], pos[1]])
        if len(stack) == 0:
            stack.append(pos)

    return tabkod3


def file_norm_tab(file_in, file_out):
    if file_in and file_out:
        tabkod = norm_tab(x1)
        for pos in tabkod:
            file_out.write((" " * 4) * pos[0] + pos[1].replace("\n", "") + "\n")
        return True
    return False


def convert_js(stream_in, stream_out):
    if stream_in and stream_out:
        tabkod = norm_tab(stream_in)
        tabkod = reformat_js(tabkod)
        for pos in tabkod:
            stream_out.write(
                (" " * 4) * pos[0]
                + pos[1].replace("\n", "").replace("};", "}").replace(";;", ";")
                + "\n"
            )
        return True
    return False


class NormParser(Parser):
    def __init__(self):
        self.txt = io.StringIO()
        self.tab = 0
        Parser.__init__(self)

    def _remove_spaces(self, value):
        return value.strip()

    def _print_attr(self, attr):
        ret = ""
        for pos in attr:
            if ret != "":
                ret += ",,,"
            if pos[1]:
                ret += pos[0] + "=" + pos[1]
            else:
                ret += pos[0]
        return ret

    def handle_starttag(self, tag, attrs):
        self.txt.write("\n")
        self.txt.write((" " * self.tab) * 4)
        self.txt.write(tag + " " + self._print_attr(attrs))
        self.tab += 1

    def handle_endtag(self, tag):
        self.tab -= 1

    def handle_startendtag(self, tag, lattrs):
        self.handle_starttag(tag, lattrs)
        self.handle_endtag(tag)

    def handle_data(self, data):
        if self._remove_spaces(data).replace("\n", "") != "":
            self.txt.write("...")
            self.txt.write(self._remove_spaces(data).replace("\n", "\\n"))

    def process(self, data):
        self.feed(data)


class IndentHtmlParser(NormParser):
    def _print_attr(self, attr):
        ret = ""
        for pos in attr:
            if ret != "":
                ret += ",,,"
            if pos[1]:
                ret += pos[0] + "=" + pos[1]
            else:
                ret += pos[0]
        return ret

    def handle_starttag(self, tag, attrs):
        self.txt.write("\n")
        self.txt.write((" " * self.tab) * 4)
        self.txt.write(self.get_starttag_text())
        self.tab += 1

    def handle_endtag(self, tag):
        self.tab -= 1
        if self.tab < 0:
            self.tab = 0
        self.txt.write("\n")
        self.txt.write((" " * self.tab) * 4)
        self.txt.write("</" + tag + ">\n")

    def handle_data(self, data):
        self.txt.write("\n")
        self.txt.write((" " * self.tab) * 4)
        tmp = ("\n" + (" " * self.tab) * 4).join([x.strip() for x in data.split("\n")])
        self.txt.write(tmp)


def norm_html(txt):
    n = NormParser()
    ret = n.process(txt)
    return ret


def indent_html(txt):
    try:
        n = IndentHtmlParser()
        ret = n.process(txt)
        lines = ret.split("\n")
        lines = [x for x in lines if x.strip() != ""]
        ret = "\n".join(lines)
    except:
        ret = txt
    return ret


if __name__ == "__main__":
    if False:
        print("x1")
        f_in = open("./test/test11.html", "r")
        print("x2", f_in)
        f_out = open("./test/test11.ihtml", "w")
        print("x3", f_out)

        ret = norm_html(f_in.read())
        f_out.write(ret)
        f_in.close()
        f_out.close()

    if True:
        print("x1")
        f_in = open("./test/test11.ihtml", "r")
        print("x2", f_in)
        f_out = open("./test/_test11.html", "w")
        print("x3", f_out)

        ret = indent_html(f_in.read())
        f_out.write(ret)
        f_in.close()
        f_out.close()
