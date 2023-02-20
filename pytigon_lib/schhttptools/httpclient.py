#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Pu`blic License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

# Pytigon - wxpython and django application framework

# author: "Sławomir Chołaj (slawomir.cholaj@gmail.com)"
# copyright: "Copyright (C) ????/2012 Sławomir Chołaj"
# license: "LGPL 3.0"
# version: "0.1a"

"""Module contains classed for define http client

"""

import base64
import os
import mimetypes

from django.conf import settings
import asyncio

from threading import Thread

from pytigon_lib.schfs import open_file, get_vfs
from pytigon_lib.schfs.vfstools import norm_path
from pytigon_lib.schtools.schjson import json_loads
from pytigon_lib.schtools.platform_info import platform_name

if platform_name() != "Emscripten":
    import httpx

from pytigon_lib.schhttptools.asgi_bridge import get_or_post, websocket
from pytigon_lib.schtools.platform_info import platform_name
from django.core.wsgi import get_wsgi_application
from django.test import Client

import threading
import logging

LOGGER = logging.getLogger("httpclient")

ASGI_APPLICATION = None
FORCE_WSGI = False


def decode(bstr, dec="utf-8"):
    if type(bstr) == bytes:
        return bstr.decode(dec)
    else:
        return bstr


def init_embeded_django():
    global ASGI_APPLICATION
    import django

    if platform_name() == "Emscripten":
        django.setup()
        ASGI_APPLICATION = True
    elif FORCE_WSGI:
        ASGI_APPLICATION = get_wsgi_application()
    else:
        django.setup()
        from channels.routing import get_default_application

        ASGI_APPLICATION = get_default_application()

    import pytigon.schserw.urls


BLOCK = False
COOKIES_EMBEDED = {}
COOKIES = {}
HTTP_LOCK = threading.Lock()

HTTP_ERROR_FUNC = None


def set_http_error_func(func):
    global HTTP_ERROR_FUNC
    HTTP_ERROR_FUNC = func


HTTP_IDLE_FUNC = None


def set_http_idle_func(func):
    global HTTP_IDLE_FUNC
    HTTP_IDLE_FUNC = func


def schurljoin(base, address):
    if (
        address
        and len(address) > 0
        and base
        and len(base) > 0
        and base[-1] == "/"
        and address[0] == "/"
        and not base.endswith("://")
    ):
        return base + address[1:]
    else:
        return base + address


class RetHttp:
    def __init__(self, url, ret_message):
        self.url = url
        self.history = None
        self.cookies = {}
        for key, value in ret_message.items():
            if key == "body":
                self.content = value
            elif key == "headers":
                self.headers = {}
                if type(value) == dict:
                    value = value.items()
                for pos in value:
                    if decode(pos[0]).lower() == "set-cookie":
                        x = decode(pos[1])
                        x2 = x.split("=", 1)
                        self.cookies[x2[0]] = x2[1]
                    else:
                        self.headers[decode(pos[0]).lower()] = decode(pos[1])

            elif key == "status":
                if type(value) == tuple:
                    self.status_code = value[0]
                else:
                    self.status_code = value
            elif key == "type":
                self.type = value
            elif key == "cookies":
                self.cookies = value
            elif key == "history":
                self.history = value
            elif key == "url":
                self.url = value


CLIENT = None
# Client(HTTP_USER_AGENT = 'Emscripten' if platform_name() == "Emscripten" else "Pytigon")


def emscripten_asgi_or_wsgi_get_or_post(
    application, url, headers, params={}, post=False, ret=[], user_agent="Pytigon"
):
    global CLIENT
    _user_agent = None
    if not CLIENT:
        CLIENT = Client(
            HTTP_USER_AGENT="Emscripten"
            if platform_name() == "Emscripten"
            else user_agent
        )

    if user_agent and CLIENT.defaults["HTTP_USER_AGENT"] != user_agent:
        _user_agent = CLIENT.defaults["HTTP_USER_AGENT"]
        CLIENT.defaults["HTTP_USER_AGENT"] = user_agent

    url2 = url.replace("http://127.0.0.2", "")
    if post:
        params2 = {}
        for key, value in params.items():
            if type(value) == bytes:
                params2[key] = value.decode("utf-8")
            else:
                params2[key] = value
        response = CLIENT.post(url2, params2)
    else:
        response = CLIENT.get(url2)

    result = {}
    result["headers"] = dict(response.headers)
    result["type"] = "http.response.starthttp.response.body"
    result["status"] = response.status_code
    result["body"] = response.getvalue()
    result["more_body"] = False
    if response.status_code in (301, 302):
        return asgi_or_wsgi_get_or_post(
            application,
            response.headers["Location"],
            headers,
            params,
            post,
            ret,
            user_agent,
        )

    ret.append(result)

    if _user_agent:
        CLIENT.defaults["HTTP_USER_AGENT"] = _user_agent


def asgi_or_wsgi_get_or_post(
    application, url, headers, params={}, post=False, ret=[], user_agent="pytigon"
):
    if True or platform_name() == "Emscripten" or FORCE_WSGI:
        return emscripten_asgi_or_wsgi_get_or_post(
            application, url, headers, params, post, ret, user_agent
        )
    else:
        event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(event_loop)
        ret2 = asyncio.get_event_loop().run_until_complete(
            get_or_post(application, url, headers, params=params, post=post)
        )
        ret.append(ret2)


def requests_request(method, url, argv, ret=[]):
    ret2 = httpx.request(method, url, **argv)
    ret.append(ret2)


def request(method, url, direct_access, argv, app=None, user_agent="pytigon"):
    global ASGI_APPLICATION
    ret = []
    if direct_access and ASGI_APPLICATION:
        post = True if method == "post" else False
        h = argv["headers"]
        headers = []
        for key, value in h.items():
            headers.append((key.encode("utf-8"), value.encode("utf-8")))
        cookies = ""
        if "cookies" in argv:
            for key, value in argv["cookies"].items():
                value2 = value.split(";", 1)[0]
                cookies += f"{key}={value2};"
        if cookies:
            headers.append((b"cookie", cookies.encode("utf-8")))

        if post:
            if platform_name() == "Emscripten" or FORCE_WSGI:
                asgi_or_wsgi_get_or_post(
                    ASGI_APPLICATION,
                    url.replace("http://127.0.0.2", ""),
                    headers,
                    argv["data"],
                    post,
                    ret,
                    user_agent,
                )
            else:
                t = Thread(
                    target=asgi_or_wsgi_get_or_post,
                    args=(
                        ASGI_APPLICATION,
                        url.replace("http://127.0.0.2", ""),
                        headers,
                        argv["data"],
                        post,
                        ret,
                        user_agent,
                    ),
                    daemon=True,
                )
                t.start()
                if app:
                    try:
                        while t.is_alive():
                            app.Yield()
                    except:
                        t.join()
                else:
                    t.join()
        else:
            if platform_name() == "Emscripten" or FORCE_WSGI:
                asgi_or_wsgi_get_or_post(
                    ASGI_APPLICATION,
                    url.replace("http://127.0.0.2", ""),
                    headers,
                    {},
                    post,
                    ret,
                    user_agent,
                )
            else:
                t = Thread(
                    target=asgi_or_wsgi_get_or_post,
                    args=(
                        ASGI_APPLICATION,
                        url.replace("http://127.0.0.2", ""),
                        headers,
                        {},
                        post,
                        ret,
                        user_agent,
                    ),
                    daemon=True,
                )
                t.start()
                if app:
                    try:
                        while t.is_alive():
                            app.Yield()
                    except:
                        t.join()
                else:
                    t.join()
        return RetHttp(url, ret[0])
    else:
        if app:
            if platform_name() == "Emscripten" or FORCE_WSGI:
                requests_request(method, url, argv, ret)
            else:
                t = Thread(
                    target=requests_request, args=(method, url, argv, ret), daemon=True
                )
                t.start()
                try:
                    while t.is_alive():
                        app.Yield()
                except:
                    t.join()
        else:
            requests_request(method, url, argv, ret)
        return ret[0]


class HttpResponse:
    def __init__(
        self, url, ret_code=200, response=None, content=None, ret_content_type=None
    ):
        self.url = url
        self.ret_code = ret_code
        self.response = response
        self.content = content
        self.ret_content_type = ret_content_type
        self.new_url = url

    def process_response(self, http_client, parent, post_request):
        global COOKIES
        global COOKIES_EMBEDED
        global BLOCK
        global HTTP_ERROR_FUNC

        if self.url.startswith("http://127.0.0.2/"):
            cookies = COOKIES_EMBEDED
        else:
            cookies = COOKIES

        self.content = self.response.content
        self.ret_code = self.response.status_code

        if self.response.status_code != 200:
            LOGGER.error({"address": self.url, "httpcode": self.response.status_code})
            if self.response.status_code == 500:
                LOGGER.error({"content": self.content})

        if "content-type" in self.response.headers:
            self.ret_content_type = self.response.headers["content-type"]
        else:
            self.ret_content_type = None

        if self.response.history:
            for r in self.response.history:
                for key, value in r.cookies.items():
                    cookies[key] = value

        if self.response.cookies:
            for key, value in self.response.cookies.items():
                cookies[key] = value

        if self.ret_content_type and "text/" in self.ret_content_type:
            if "Traceback" in str(self.content) and "copy-and-paste" in str(
                self.content
            ):
                if HTTP_ERROR_FUNC:
                    BLOCK = True
                    HTTP_ERROR_FUNC(parent, self.content)
                    BLOCK = False
                else:
                    with open(
                        os.path.join(settings.DATA_PATH, "last_error.html"), "wb"
                    ) as f:
                        f.write(self.content)
                self.ret_content_type = "500"
                self.content = b""
                return

        if (
            not post_request
            and not "?" in self.url
            and type(self.content) == bytes
            and (b"Cache-control" in self.content or "/plugins" in self.url)
        ):
            http_client.http_cache[self.url] = (self.ret_content_type, self.content)

        if type(self.response.url) == str:
            self.new_url = self.response.url
        else:
            self.new_url = self.response.url.path

    def ptr(self):
        """Return request content"""
        return self.content

    def str(self):
        """Return request content converted to string"""
        dec = "utf-8"
        if self.ret_content_type:
            if "text" in self.ret_content_type:
                if "iso-8859-2" in self.ret_content_type:
                    dec = "iso-8859-2"
                ret = decode(self.content, dec)
            else:
                if "application/json" in self.ret_content_type:
                    ret = decode(self.content, "utf-8")
                else:
                    ret = self.content
        else:
            ret = self.content
        return ret

    def json(self):
        return json_loads(self.str())
        # return self.http.json()

    def to_python(self):
        """Return request content in json format converted to python object"""
        return json_loads(self.str())


class HttpClient:
    """Http client class"""

    def __init__(self, address=""):
        """Constructor

        Args:
            address: base address for http requests
        """
        if address:
            self.base_address = address
        else:
            self.base_address = "http://127.0.0.2"
        self.http_cache = {}
        self.app = None

    def close(self):
        pass

    def post(
        self,
        parent,
        address_str,
        parm=None,
        upload=False,
        credentials=False,
        user_agent=None,
        json_data=False,
        callback=None,
    ):
        """Prepare post request to the http server

        Args:
            parent - parent wx.Window derived object
            address_str - request address
            param - python dict with request parameters
            upload - True or False
            credentials - default False
            user_agent - default None
            json_data - send parm to server in json format
        """
        return self.get(
            parent,
            address_str,
            parm,
            upload,
            credentials,
            user_agent,
            True,
            json_data=json_data,
        )

    def get(
        self,
        parent,
        address_str,
        parm=None,
        upload=False,
        credentials=False,
        user_agent="pytigon",
        post_request=False,
        json_data=False,
        callback=None,
        for_vfs=True,
    ):
        """Prepare get request to the http server

        Args:
            parent - parent wx.Window derived object
            address_str - request address
            param - python dict with request parameters
            upload - True or False
            credentials - default False
            user_agent - default None
        """

        if address_str.startswith("data:"):
            x = address_str.split(",", 1)
            if len(x) == 2:
                t = x[0][5:].split(";")
                if t[1].strip() == "base64":
                    return HttpResponse(
                        address_str,
                        content=base64.b64decode(x[1].encode("utf-8")),
                        ret_content_type=t[0],
                    )
            return HttpResponse(address_str, 500)

        global COOKIES
        global COOKIES_EMBEDED
        global BLOCK
        if BLOCK:
            while BLOCK:
                try:
                    if HTTP_IDLE_FUNC:
                        HTTP_IDLE_FUNC()
                except:
                    return HttpResponse(address_str, 500)

        self.content = ""
        if address_str[0] == "^":
            address = "http://127.0.0.2/plugins/" + address_str[1:]
        else:
            address = address_str

        if address[0] == "/" or address[0] == ".":
            adr = schurljoin(self.base_address, address)
        else:
            adr = address

        # adr = replace_dot(adr)
        adr = norm_path(adr)
        # adr = adr.replace(' ', '%20')

        if adr.startswith("http://127.0.0.2/"):
            cookies = COOKIES_EMBEDED
            direct_access = True
        else:
            cookies = COOKIES
            direct_access = False

        LOGGER.info(adr)

        if not post_request and not "?" in adr:
            if adr in self.http_cache:
                return HttpResponse(
                    adr,
                    content=self.http_cache[adr][1],
                    ret_content_type=self.http_cache[adr][0],
                )

        if (
            adr.startswith("http://127.0.0")
            and ("/static/" in adr or "/site_media" in adr)
            and not "?" in adr
        ):
            path = adr.replace("http://127.0.0.2", "")

            try:
                ext = "." + path.split(".")[-1]
                if ext in mimetypes.types_map:
                    mt = mimetypes.types_map[ext]
                else:
                    mt = "text/html"

                with open_file(path, "rb", for_vfs=for_vfs) as f:
                    ret = HttpResponse(
                        adr,
                        content=f.read(),
                        ret_content_type=mt,
                    )

                return ret
            except:
                if for_vfs:
                    print("Static file load error: ", get_vfs().getsyspath(path))
                else:
                    print("Static file load error: ", path)
                return HttpResponse(adr, 400, content=b"", ret_content_type="text/html")

        if adr.startswith("file://"):
            file_name = adr[7:]
            if file_name[0] == "/" and file_name[2] == ":":
                file_name = file_name[1:]

            ext = "." + file_name.split(".")[-1]
            if ext in mimetypes.types_map:
                mt = mimetypes.types_map[ext]
            else:
                mt = "text/html"

            with open_file(file_name, "rb", for_vfs=for_vfs) as f:
                ret = HttpResponse(adr, content=f.read(), ret_content_type=mt)
            return ret

        if parm == None:
            parm = {}

        headers = {}
        if user_agent:
            headers["User-Agent"] = user_agent
        headers["Referer"] = adr

        # argv = {"headers": headers, "allow_redirects": True, "cookies": cookies}
        argv = {"headers": headers, "follow_redirects": True, "cookies": cookies}
        if credentials:
            argv["auth"] = credentials

        method = "get"
        if post_request:
            method = "post"

            if json_data:
                argv["json"] = parm
            else:
                argv["data"] = parm

            if "csrftoken" in cookies:
                headers["X-CSRFToken"] = cookies["csrftoken"].split(";", 1)[0]

            if upload:
                files = {}
                for key, value in parm.items():
                    if type(value) == str and value.startswith("@"):
                        if os.path.exists(value[1:]):
                            files[key] = open(value[1:], "rb")
                for key in files:
                    del parm[key]

                if direct_access:
                    if not "data" in argv:
                        argv["data"] = {}
                    for key, value in files.items():
                        argv["data"][key] = value
                else:
                    argv["files"] = files
            else:
                if json_data:
                    argv["json"] = parm
        else:
            argv["data"] = parm

        response = request(method, adr, direct_access, argv, self.app, user_agent)
        http_response = HttpResponse(adr, response=response)
        http_response.process_response(self, parent, post_request)

        return http_response

    def show(self, parent):
        if HTTP_ERROR_FUNC:
            HTTP_ERROR_FUNC(parent, self.content)


class AppHttp(HttpClient):
    """Extended version of HttpClient"""

    def __init__(self, address, app):
        """Constructor

        Args:
            address - base request address
            app - application name
        """
        HttpClient.__init__(self, address)
        self.app = app


def join_http_path(base, ext):
    if base.endswith("/") and ext.startswith("/"):
        return base + ext[1:]
    else:
        return base + ext


async def local_websocket(path, input_queue, output):
    global COOKIES_EMBEDED
    global ASGI_APPLICATION

    user_agent = ""
    headers = []
    headers.append((b"User-Agent", user_agent))
    headers.append((b"Referer", path))

    cookies = ""
    if COOKIES_EMBEDED:
        if "csrftoken" in COOKIES_EMBEDED:
            headers.append(
                ("X-CSRFToken", COOKIES_EMBEDED["csrftoken"].split(";", 1)[0])
            )
        for key, value in COOKIES_EMBEDED.items():
            value2 = value.split(";", 1)[0]
            cookies += f"{key}={value2};"
    if cookies:
        headers.append((b"cookie", cookies.encode("utf-8")))

    return await websocket(ASGI_APPLICATION, path, headers, input_queue, output)
