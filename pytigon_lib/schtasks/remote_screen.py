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

import logging
from html.parser import HTMLParser


class OnlyTxtParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.txt = []

    def handle_data(self, data):
        self.txt.append(data.strip())

    def to_txt(self):
        return " ".join(self.txt)


def to_txt(html_txt):
    try:
        parser = OnlyTxtParser()
        parser.feed(html_txt)
        return parser.to_txt()
    except:
        return ""


class RemoteScreen:
    def __init__(self, cproxy, direction="down"):
        self.cproxy = cproxy
        self.direction = direction

    def __enter__(self):
        self.raw_print("<div class='log'></div>===>>")
        return self

    def __exit__(self, type, value, traceback):
        pass

    def raw_print(self, html_txt):
        if self.cproxy:
            self.cproxy.send_event(html_txt)
        else:
            print(html_txt)

    def _log(self, html_txt, p_class, fun, operator):
        if self.direction == "down":
            operator2 = operator
        else:
            operator2 = operator.replace(">>", "<<")

        if self.cproxy:
            self.raw_print(f"<p class='{p_class}'>" + html_txt + "</p>" + operator2)
        else:
            if fun:
                fun(to_txt(html_txt))

    def log(self, html_txt):
        return self._log(html_txt, "log-line", logging.info, "===>>.log")

    def info(self, html_txt):
        return self._log(html_txt, "text-info", logging.info, "===>>.log")

    def warning(self, html_txt):
        return self._log(html_txt, "text-warning", logging.warning, "===>>.log")

    def error(self, html_txt):
        return self._log(html_txt, "text-white bg-danger", logging.error, "===>>.log")
