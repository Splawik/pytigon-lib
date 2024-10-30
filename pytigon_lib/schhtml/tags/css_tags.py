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

from pytigon_lib.schhtml.basehtmltags import BaseHtmlElemParser, register_tag_map


class Css(BaseHtmlElemParser):
    """Load CSS definitions from STYLE tag"""

    def __init__(self, parent, parser, tag, attrs):
        BaseHtmlElemParser.__init__(self, parent, parser, tag, attrs)

    def close(self):
        """parse CSS definitions"""
        self.parser.css.parse_str("".join(self.data))


register_tag_map("style", Css)


class CssLink(BaseHtmlElemParser):
    """
    Load CSS definitions from LINK tag
    """

    def __init__(self, parent, parser, tag, attrs):
        BaseHtmlElemParser.__init__(self, parent, parser, tag, attrs)

    def close(self):
        """
        Load CSS definitions from LINK tag
        """
        if "href" in self.attrs:
            href = self.attrs["href"]
            # skip favicon
            if ".ico" in href:
                return
            # get http object
            http = self.parser.get_http_object()
            try:
                response = http.get(self, href)
                if response.ret_code == 404:
                    css_txt = None
                else:
                    css_txt = response.str()
            except:
                css_txt = None
            # parse css definitions
            if css_txt:
                self.parser.css.parse_str(css_txt)


register_tag_map("link", CssLink)
