"""Module contains classes for defining HTTP client."""

import base64
import os
import mimetypes
import threading
import logging
import httpx
from threading import Thread
from django.conf import settings
from django.core.wsgi import get_wsgi_application
from django.test import Client
from django.contrib.staticfiles import finders

from pytigon_lib.schfs import open_file, get_vfs
from pytigon_lib.schfs.vfstools import norm_path
from pytigon_lib.schtools.schjson import json_loads
from pytigon_lib.schtools.platform_info import platform_name
from pytigon_lib.schhttptools.asgi_bridge import websocket

LOGGER = logging.getLogger("httpclient")

ASGI_APPLICATION = None
FORCE_WSGI = False
BLOCK = False
COOKIES_EMBEDED = {}
COOKIES = {}
HTTP_LOCK = threading.Lock()
HTTP_ERROR_FUNC = None
HTTP_IDLE_FUNC = None


def decode(bstr, dec="utf-8"):
    """Decode bytes to string."""
    return bstr.decode(dec) if isinstance(bstr, bytes) else bstr


def init_embeded_django():
    """Initialize embedded Django application."""
    global ASGI_APPLICATION
    import django

    if platform_name() == "Emscripten" or FORCE_WSGI:
        django.setup()
        ASGI_APPLICATION = get_wsgi_application()
    else:
        django.setup()
        from channels.routing import get_default_application

        ASGI_APPLICATION = get_default_application()
    import pytigon.schserw.urls


def set_http_error_func(func):
    """Set HTTP error handling function."""
    global HTTP_ERROR_FUNC
    HTTP_ERROR_FUNC = func


def set_http_idle_func(func):
    """Set HTTP idle handling function."""
    global HTTP_IDLE_FUNC
    HTTP_IDLE_FUNC = func


def schurljoin(base, address):
    """Join base URL and address."""
    if (
        address
        and base
        and base[-1] == "/"
        and address[0] == "/"
        and not base.endswith("://")
    ):
        return base + address[1:]
    return base + address


class RetHttp:
    """Wrapper for HTTP response."""

    def __init__(self, url, ret_message):
        self.url = url
        self.history = None
        self.cookies = {}
        for key, value in ret_message.items():
            if key == "body":
                self.content = value
            elif key == "headers":
                self.headers = {}
                for pos in value.items() if isinstance(value, dict) else value:
                    if decode(pos[0]).lower() == "set-cookie":
                        x = decode(pos[1])
                        x2 = x.split("=", 1)
                        self.cookies[x2[0]] = x2[1]
                    else:
                        self.headers[decode(pos[0]).lower()] = decode(pos[1])
            elif key == "status":
                self.status_code = value[0] if isinstance(value, tuple) else value
            elif key == "type":
                self.type = value
            elif key == "cookies":
                self.cookies = value
            elif key == "history":
                self.history = value
            elif key == "url":
                self.url = value


CLIENT = None


def asgi_or_wsgi_get_or_post(
    application, url, headers, params={}, post=False, ret=[], user_agent="Pytigon"
):
    """Handle GET or POST request for Emscripten or WSGI."""
    global CLIENT
    if not CLIENT:
        CLIENT = Client(
            HTTP_USER_AGENT=(
                "Emscripten" if platform_name() == "Emscripten" else user_agent
            )
        )
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

    result = {
        "headers": dict(response.headers),
        "type": "http.response.starthttp.response.body",
        "status": response.status_code,
        "body": response.getvalue(),
        "more_body": False,
    }
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


def requests_request(method, url, argv, ret=[]):
    """Perform HTTP request using httpx."""
    ret2 = httpx.request(method, url, **argv)
    ret.append(ret2)


def request(method, url, direct_access, argv, app=None, user_agent="pytigon"):
    """Perform HTTP request."""
    global ASGI_APPLICATION
    ret = []
    if direct_access and ASGI_APPLICATION:
        post = method == "post"
        headers = [
            (key.encode("utf-8"), value.encode("utf-8"))
            for key, value in argv["headers"].items()
        ]
        cookies = ";".join(
            f"{key}={value.split(';', 1)[0]}"
            for key, value in argv.get("cookies", {}).items()
        )
        if cookies:
            headers.append((b"cookie", cookies.encode("utf-8")))
        if platform_name() == "Emscripten" or FORCE_WSGI:
            asgi_or_wsgi_get_or_post(
                ASGI_APPLICATION,
                url.replace("http://127.0.0.2", ""),
                headers,
                argv.get("data", {}),
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
                    argv.get("data", {}),
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
    """HTTP response wrapper."""

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
        """Process HTTP response."""
        global COOKIES, COOKIES_EMBEDED, BLOCK, HTTP_ERROR_FUNC
        cookies = (
            COOKIES_EMBEDED if self.url.startswith("http://127.0.0.2/") else COOKIES
        )
        self.content = self.response.content
        self.ret_code = self.response.status_code
        if self.response.status_code != 200:
            LOGGER.error({"address": self.url, "httpcode": self.response.status_code})
            if self.response.status_code == 500:
                LOGGER.error({"content": self.content})
        self.ret_content_type = self.response.headers.get("content-type")
        if self.response.history:
            for r in self.response.history:
                for key, value in r.cookies.items():
                    cookies[key] = value
        if self.response.cookies:
            for key, value in self.response.cookies.items():
                cookies[key] = value
        if (
            self.ret_content_type
            and "text/" in self.ret_content_type
            and "Traceback" in str(self.content)
            and "copy-and-paste" in str(self.content)
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
            and "?" not in self.url
            and isinstance(self.content, bytes)
            and (b"Cache-control" in self.content or "/plugins" in self.url)
        ):
            http_client.http_cache[self.url] = (self.ret_content_type, self.content)
        self.new_url = (
            self.response.url
            if isinstance(self.response.url, str)
            else self.response.url.path
        )

    def ptr(self):
        """Return request content."""
        return self.content

    def str(self):
        """Return request content as string."""
        dec = (
            "iso-8859-2"
            if self.ret_content_type and "iso-8859-2" in self.ret_content_type
            else "utf-8"
        )
        return (
            decode(self.content, dec)
            if self.ret_content_type and "text" in self.ret_content_type
            else self.content
        )

    def json(self):
        """Return request content as JSON."""
        return json_loads(self.str())

    def to_python(self):
        """Return request content as Python object."""
        return json_loads(self.str())


class HttpClient:
    """HTTP client class."""

    def __init__(self, address=""):
        """Initialize HTTP client."""
        self.base_address = address if address else "http://127.0.0.2"
        self.http_cache = {}
        self.app = None

    def close(self):
        """Close HTTP client."""
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
        """Prepare POST request."""
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
        """Prepare GET request."""
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
        global COOKIES, COOKIES_EMBEDED, BLOCK
        if BLOCK:
            while BLOCK:
                try:
                    if HTTP_IDLE_FUNC:
                        HTTP_IDLE_FUNC()
                except:
                    return HttpResponse(address_str, 500)
        self.content = ""
        address = (
            "http://127.0.0.2/plugins/" + address_str[1:]
            if address_str[0] == "^"
            else address_str
        )
        adr = (
            schurljoin(self.base_address, address)
            if address[0] in ("/", ".")
            else address
        )
        adr = norm_path(adr)
        if adr.startswith("http://127.0.0.2") or self.base_address.startswith(
            "http://127.0.0.2"
        ):
            cookies = COOKIES_EMBEDED
            direct_access = True
        else:
            cookies = COOKIES
            direct_access = False
        LOGGER.info(adr)
        if not post_request and "?" not in adr and adr in self.http_cache:
            return HttpResponse(
                adr,
                content=self.http_cache[adr][1],
                ret_content_type=self.http_cache[adr][0],
            )
        if (
            adr.startswith("http://127.0.0")
            and ("/static/" in adr or "/site_media" in adr)
            and "?" not in adr
        ):
            path = adr.replace("http://127.0.0.2", "")
            try:
                ext = "." + path.split(".")[-1]
                mt = mimetypes.types_map.get(ext, "text/javascript")
                if path.startswith(settings.STATIC_URL):
                    path = finders.find(path[len(settings.STATIC_URL) :])
                    for_vfs = False
                with open_file(path, "rb", for_vfs=for_vfs) as f:
                    content = f.read()
                    ret_http = RetHttp(
                        adr,
                        {
                            "body": content,
                            "headers": {"Content-Type": mt},
                            "status": 200,
                        },
                    )

                    return HttpResponse(
                        adr, content=content, response=ret_http, ret_content_type=mt
                    )
            except:
                print(
                    "Static file load error: ",
                    get_vfs().getsyspath(path) if for_vfs else path,
                )
                return HttpResponse(adr, 400, content=b"", ret_content_type="text/html")
        if adr.startswith("file://"):
            file_name = adr[7:]
            if file_name[0] == "/" and file_name[2] == ":":
                file_name = file_name[1:]
            if file_name.startswith(".") and for_vfs:
                file_name = "/cwd" + file_name[1:]
            ext = "." + file_name.split(".")[-1]
            mt = mimetypes.types_map.get(ext, "text/html")
            with open_file(file_name, "rb", for_vfs=for_vfs) as f:
                return HttpResponse(adr, content=f.read(), ret_content_type=mt)
        if parm is None:
            parm = {}
        headers = (
            {"User-Agent": user_agent, "Referer": adr}
            if user_agent
            else {"Referer": adr}
        )
        argv = {"headers": headers, "follow_redirects": True, "cookies": cookies}
        if credentials:
            argv["auth"] = credentials
        method = "post" if post_request else "get"
        if post_request:
            if json_data:
                argv["json"] = parm
            else:
                argv["data"] = parm
            if "csrftoken" in cookies:
                headers["X-CSRFToken"] = cookies["csrftoken"].split(";", 1)[0]
            if upload:
                files = {
                    key: open(value[1:], "rb")
                    for key, value in parm.items()
                    if isinstance(value, str)
                    and value.startswith("@")
                    and os.path.exists(value[1:])
                }
                for key in files:
                    del parm[key]
                if direct_access:
                    if "data" not in argv:
                        argv["data"] = {}
                    for key, value in files.items():
                        argv["data"][key] = value
                else:
                    argv["files"] = files
        else:
            argv["data"] = parm
        response = request(method, adr, direct_access, argv, self.app, user_agent)
        http_response = HttpResponse(adr, response=response)
        http_response.process_response(self, parent, post_request)
        return http_response

    def show(self, parent):
        """Show HTTP error."""
        if HTTP_ERROR_FUNC:
            HTTP_ERROR_FUNC(parent, self.content)


class AppHttp(HttpClient):
    """Extended version of HttpClient."""

    def __init__(self, address, app):
        """Initialize AppHttp."""
        HttpClient.__init__(self, address)
        self.app = app


def join_http_path(base, ext):
    """Join HTTP paths."""
    return base + ext[1:] if base.endswith("/") and ext.startswith("/") else base + ext


async def local_websocket(path, input_queue, output):
    """Handle local WebSocket connection."""
    global COOKIES_EMBEDED, ASGI_APPLICATION
    user_agent = ""
    headers = [(b"User-Agent", user_agent), (b"Referer", path)]
    cookies = ";".join(
        f"{key}={value.split(';', 1)[0]}" for key, value in COOKIES_EMBEDED.items()
    )
    if cookies:
        headers.append((b"cookie", cookies.encode("utf-8")))
    if "csrftoken" in COOKIES_EMBEDED:
        headers.append(("X-CSRFToken", COOKIES_EMBEDED["csrftoken"].split(";", 1)[0]))
    return await websocket(ASGI_APPLICATION, path, headers, input_queue, output)
