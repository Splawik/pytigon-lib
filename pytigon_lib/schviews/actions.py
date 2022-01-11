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


from django.http import HttpResponse

_NEW_ROW_OK_HTML = """
<head>
    <meta name="RETURN" content="$$RETURN_NEW_ROW_OK" />
</head>
"""

_NEW_ROW_OK_SHTML = """
<head>
    <meta name="RETURN" content="$$RETURN_OK" />
    <meta name="target" content="code" />
</head>
<body>
    <script language=python>
page = self.get_parent_page().get_parent_page()
if page:
    page.signal('return_new_row', id=%s, title="%s")
self.ok()
    </script>
</body>
"""

_UPDATE_ROW_OK_HTML = """
<head>
    <meta name="RETURN" content="$$RETURN_UPDATE_ROW_OK" />
</head>
"""

_UPDATE_ROW_OK_SHTML = """
<head>
    <meta name="RETURN" content="$$RETURN_OK" />
    <meta name="target" content="code" />
</head>
<body>
    <script language=python>
page = self.get_parent_page().get_parent_page()
if page:
    page.signal('return_updated_row', id=%s, title="%s")
self.ok()
    </script>
</body>
"""

_OK_HTML = """
<head>
    <meta name="RETURN" content="$$RETURN_OK" />
</head>
"""

_REFRESH_HTML = """
<head>
    <meta name="RETURN" content="$$RETURN_REFRESH" />
</head>
"""

_REFRESH_PARENT_HTML = """
<head>
    <meta name="RETURN" content="$$RETURN_REFRESH_PARENT" />
</head>
"""

_RELOAD_HTML = """
<head>
    <meta name="RETURN" content="$$RETURN_RELOAD" />
</head>
<body>
%s 
</body>
"""

_CANCEL_HTML = """
<head>
    <meta name="RETURN" content="$$RETURN_CANCEL" />
</head>
"""

_ERROR_HTML = """
<head>
    <meta name="RETURN" content="$$RETURN_ERROR" />
</head>
<body>
%s
</body>
"""


def new_row_ok(request, id, title):
    if not "HTTP_USER_AGENT" in request.META or (
        request.META["HTTP_USER_AGENT"]
        and request.META["HTTP_USER_AGENT"].lower().startswith("py")
    ):
        return HttpResponse(_NEW_ROW_OK_SHTML % (id, title))
    else:
        return HttpResponse(_NEW_ROW_OK_HTML + "id:" + str(id))


def update_row_ok(request, id, title):
    if not "HTTP_USER_AGENT" in request.META or (
        request.META["HTTP_USER_AGENT"]
        and request.META["HTTP_USER_AGENT"].lower().startswith("py")
    ):
        return HttpResponse(_UPDATE_ROW_OK_SHTML % (id, title))
    else:
        return HttpResponse(_UPDATE_ROW_OK_HTML + "id:" + str(id))


def ok(request):
    return HttpResponse(_OK_HTML)


def refresh(request):
    return HttpResponse(_REFRESH_HTML)


def refresh_parent(request):
    return HttpResponse(_REFRESH_PARENT_HTML)


def reload(request, new_html):
    return HttpResponse(_RELOAD_HTML % new_html)


def cancel(request):
    return HttpResponse(_CANCEL_HTML)


def error(request, error_txt):
    return HttpResponse(_ERROR_HTML % error_txt)
