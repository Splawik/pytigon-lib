"""Module contains classes for defining HTTP client."""

import base64
import json
import logging
import mimetypes
import os
import threading
from collections import OrderedDict
from contextlib import ExitStack
from threading import Thread
from urllib.parse import urljoin

import httpx
from django.conf import settings
from django.core.wsgi import get_wsgi_application
from django.test import Client

from pytigon_lib.schfs import open_file
from pytigon_lib.schfs.vfstools import norm_path
from pytigon_lib.schhttptools.asgi_bridge import websocket
from pytigon_lib.schtools.platform_info import platform_name
from pytigon_lib.schtools.schjson import json_loads

LOGGER = logging.getLogger("httpclient")

ASGI_APPLICATION = None
FORCE_WSGI = False
BLOCK = False
BLOCK_EVENT = threading.Event()
COOKIES_EMBEDED = {}
COOKIES = {}
HTTP_LOCK = threading.Lock()
HTTP_ERROR_FUNC = None
HTTP_IDLE_FUNC = None

# Set to a value > 0 while a paint/draw event is being processed on the GUI
# thread. While painting, pumping the GTK event loop with app.Yield() would
# re-enter drawing on the same window and crash (cairo: "window already has a
# drawing context"), so the GUI thread must block instead of yielding.
IN_PAINT = 0


class EmptyResponseError(RuntimeError):
    """Raised when a request produced no response object at all.

    Returning ``None`` instead used to defer the failure to an unrelated
    ``AttributeError`` inside :meth:`HttpResponse.process_response`.
    """


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
    # Guard: init_embeded_django() can be called more than once in a process
    # (re-import, test harness), and appending every time grows the list
    # without bound.
    if "testserver" not in settings.ALLOWED_HOSTS:
        settings.ALLOWED_HOSTS.append("testserver")


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
    if address and base and base[-1] == "/" and address[0] == "/" and not base.endswith("://"):
        return base + address[1:]
    return base + address


class RetHttp:
    """Wrapper for HTTP response from the asgi/wsgi bridge.

    Parses a dictionary message from the ASGI/WSGI layer into
    response attributes compatible with httpx.Response interface.
    """

    def __init__(self, url, ret_message):
        self.url = url
        self.history = None
        self.cookies = {}
        self.content = b""
        self.status_code = 200
        self.headers = {}
        self.type = ""
        for key, value in ret_message.items():
            if key == "body":
                self.content = value
            elif key == "headers":
                self.headers = {}
                items = value.items() if isinstance(value, dict) else value
                for pos in items:
                    header_name = decode(pos[0]).lower()
                    if header_name == "set-cookie":
                        x = decode(pos[1])
                        x2 = x.split("=", 1)
                        self.cookies[x2[0]] = x2[1]
                    else:
                        self.headers[header_name] = decode(pos[1])
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
    application,
    url,
    headers,
    params=None,
    post=False,
    ret=None,
    user_agent="Pytigon",
    redirect_count=0,
    json_data=False,
):
    """Handle GET or POST request for Emscripten or WSGI."""

    if params is None:
        params = {}
    if ret is None:
        ret = []
    global CLIENT
    if not CLIENT:
        CLIENT = Client(HTTP_USER_AGENT=("Emscripten" if platform_name() == "Emscripten" else user_agent))
    url2 = url.replace("http://127.0.0.2", "")
    if post:
        if json_data:
            response = CLIENT.post(url2, json.dumps(params), content_type="application/json")
        else:
            params2 = {}
            for key, value in params.items():
                if isinstance(value, bytes):
                    params2[key] = value.decode("utf-8")
                else:
                    params2[key] = value
            json_data = False
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
    if response.status_code in (301, 302, 303, 307, 308) and redirect_count < 10:
        location = response.headers.get("Location")
        if location:
            # The Location header is often relative; re-join it with the
            # requested URL so the follow-up request is well formed.
            return asgi_or_wsgi_get_or_post(
                application,
                urljoin(response.url, location),
                headers,
                params,
                post,
                ret,
                user_agent,
                redirect_count + 1,
                json_data,
            )
    ret.append(result)


#: Module-level httpx client: reusing one Client keeps the connection pool (and
#: the TLS session) alive instead of paying a new handshake per request.
HTTPX_CLIENT = None


def _get_httpx_client():
    """Return the shared httpx.Client, creating it on first use."""
    global HTTPX_CLIENT
    if HTTPX_CLIENT is None or getattr(HTTPX_CLIENT, "is_closed", False):
        HTTPX_CLIENT = httpx.Client(
            limits=httpx.Limits(
                max_connections=32, max_keepalive_connections=16, keepalive_expiry=30.0
            ),
            follow_redirects=False,
        )
    return HTTPX_CLIENT


def requests_request(method, url, argv, ret=None):
    """Perform HTTP request using httpx."""
    if ret is None:
        ret = []
    try:
        ret2 = _get_httpx_client().request(method, url, **argv)
        ret.append(ret2)
    except Exception as e:
        ret.append(e)


def request(method, url, direct_access, argv, app=None, user_agent="pytigon"):
    """Perform HTTP request."""
    global ASGI_APPLICATION
    ret = []
    if direct_access and ASGI_APPLICATION:
        post = method == "post"
        headers = [(key.encode("utf-8"), value.encode("utf-8")) for key, value in argv["headers"].items()]
        cookies = ";".join(f"{key}={value.split(';', 1)[0]}" for key, value in argv.get("cookies", {}).items())
        if cookies:
            headers.append((b"cookie", cookies.encode("utf-8")))
        if platform_name() == "Emscripten" or FORCE_WSGI:
            asgi_or_wsgi_get_or_post(
                ASGI_APPLICATION,
                url.replace("http://127.0.0.2", ""),
                headers,
                argv.get("json", {}) if "json" in argv else argv.get("data", {}),
                post,
                ret,
                user_agent,
                0,
                "json" in argv,
            )
        else:
            t = Thread(
                target=asgi_or_wsgi_get_or_post,
                args=(
                    ASGI_APPLICATION,
                    url.replace("http://127.0.0.2", ""),
                    headers,
                    argv.get("json", {}) if "json" in argv else argv.get("data", {}),
                    post,
                    ret,
                    user_agent,
                    0,
                    "json" in argv,
                ),
                daemon=True,
            )
            t.start()
            if app:
                try:
                    if IN_PAINT:
                        t.join()
                    else:
                        while t.is_alive():
                            app.Yield()
                except Exception:
                    t.join()
            else:
                t.join()
        if ret and isinstance(ret[0], Exception):
            raise ret[0]
        if not ret:
            raise EmptyResponseError(f"No response produced for {method} {url}")
        return RetHttp(url, ret[0])
    else:
        if app:
            if platform_name() == "Emscripten" or FORCE_WSGI:
                requests_request(method, url, argv, ret)
            else:
                t = Thread(target=requests_request, args=(method, url, argv, ret), daemon=True)
                t.start()
                try:
                    if IN_PAINT:
                        t.join()
                    else:
                        while t.is_alive():
                            app.Yield()
                except Exception:
                    t.join()
        else:
            requests_request(method, url, argv, ret)
        if ret and isinstance(ret[0], Exception):
            raise ret[0]
        if not ret:
            # Returning None here would surface later as an AttributeError
            # deep inside HttpResponse.process_response().
            raise EmptyResponseError(f"No response produced for {method} {url}")
        return ret[0]


class HttpResponse:
    """HTTP response wrapper."""

    def __init__(self, url, ret_code=200, response=None, content=None, ret_content_type=None):
        self.url = url
        self.ret_code = ret_code
        self.response = response
        self.content = content
        self.ret_content_type = ret_content_type
        self.new_url = url

    def process_response(self, http_client, parent, post_request):
        """Process HTTP response."""
        global BLOCK, HTTP_ERROR_FUNC
        # Use the per-instance cookie jar from the HttpClient so that
        # concurrent clients don't share session cookies.
        cookies = http_client.cookies_embeded if self.url.startswith("http://127.0.0.2/") else http_client.cookies
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
                try:
                    HTTP_ERROR_FUNC(parent, self.content)
                finally:
                    # Without this, an exception raised by HTTP_ERROR_FUNC
                    # left BLOCK stuck True and the request loop spinning.
                    BLOCK = False
            else:
                with open(os.path.join(settings.DATA_PATH, "last_error.html"), "wb") as f:
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
            if len(http_client.http_cache) > 128:
                http_client.http_cache.popitem(last=False)
        self.new_url = self.response.url if isinstance(self.response.url, str) else self.response.url.path

    def ptr(self):
        """Return request content."""
        return self.content

    def str(self):
        """Return request content as string."""
        dec = "iso-8859-2" if self.ret_content_type and "iso-8859-2" in self.ret_content_type else "utf-8"
        return decode(self.content, dec) if self.ret_content_type and "text" in self.ret_content_type else self.content

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
        self.http_cache = OrderedDict()
        self.app = None
        # Per-instance cookie jars so that concurrent HttpClient instances
        # (e.g. serving different users in a multi-threaded server) do not
        # leak each other's session cookies through the module-level
        # COOKIES / COOKIES_EMBEDED dicts.
        self.cookies = {}
        self.cookies_embeded = {}

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
        global BLOCK
        if BLOCK:
            while BLOCK:
                if HTTP_IDLE_FUNC:
                    try:
                        HTTP_IDLE_FUNC()
                    except Exception:
                        return HttpResponse(address_str, 500)
                else:
                    BLOCK_EVENT.wait(timeout=0.1)
        self.content = ""
        address = "http://127.0.0.2/plugins/" + address_str[1:] if address_str[0] == "^" else address_str
        adr = schurljoin(self.base_address, address) if address[0] in ("/", ".") else address
        adr = norm_path(adr)
        if adr.startswith("http://127.0.0.2") or self.base_address.startswith("http://127.0.0.2"):
            cookies = self.cookies_embeded
            direct_access = True
        else:
            cookies = self.cookies
            direct_access = False
        LOGGER.info(adr)
        if not post_request and "?" not in adr and adr in self.http_cache:
            return HttpResponse(
                adr,
                content=self.http_cache[adr][1],
                ret_content_type=self.http_cache[adr][0],
            )
        if adr.startswith("http://127.0.0") and ("/static/" in adr or "/site_media" in adr) and "?" not in adr:
            path = adr.replace("http://127.0.0.2", "")
            try:
                ext = "." + path.split(".")[-1]
                mt = mimetypes.types_map.get(ext, "text/javascript")
                if path.startswith(settings.STATIC_URL):
                    path = "static/" + path[len(settings.STATIC_URL) :]
                    for_vfs = True
                with open_file(path, "rb", for_vfs=for_vfs) as f:
                    content = f.read()
                    ret_http = RetHttp(
                        adr,
                        {
                            "body": content,
                            "headers": {
                                "Content-Type": mt,
                                "cache-control": "max-age=2592000",
                            },
                            "status": 200,
                        },
                    )

                    return HttpResponse(adr, content=content, response=ret_http, ret_content_type=mt)
            except (OSError, FileNotFoundError):
                LOGGER.exception("Static file load error: %s", path)
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

        headers = {"User-Agent": user_agent, "Referer": adr} if user_agent else {"Referer": adr}
        argv = {"headers": headers, "follow_redirects": True, "cookies": cookies}
        if credentials:
            argv["auth"] = credentials
        method = "post" if post_request else "get"
        with ExitStack() as stack:
            if post_request:
                if json_data:
                    argv["json"] = parm
                else:
                    argv["data"] = parm
                if "csrftoken" in cookies:
                    headers["X-CSRFToken"] = cookies["csrftoken"].split(";", 1)[0]
                if upload:
                    files = {
                        key: stack.enter_context(open(value[1:], "rb"))
                        for key, value in parm.items()
                        if isinstance(value, str) and value.startswith("@") and os.path.exists(value[1:])
                    }
                    for key in files:
                        del parm[key]
                    if direct_access:
                        # The direct-access branch talks to the ASGI bridge,
                        # which takes plain form data. Raw open file objects
                        # cannot be encoded into that body (and would be closed
                        # by the ExitStack before the request is sent), so the
                        # bytes are read in here instead.
                        if files:
                            argv["data"] = dict(parm)
                            for key, fileobj in files.items():
                                argv["data"][key] = fileobj.read()
                        else:
                            argv["data"] = parm
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
            HTTP_ERROR_FUNC(parent, getattr(self, "content", b""))


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
    cookies = ";".join(f"{key}={value.split(';', 1)[0]}" for key, value in COOKIES_EMBEDED.items())
    if cookies:
        headers.append((b"cookie", cookies.encode("utf-8")))
    if "csrftoken" in COOKIES_EMBEDED:
        headers.append((b"X-CSRFToken", COOKIES_EMBEDED["csrftoken"].split(";", 1)[0].encode("utf-8")))
    return await websocket(ASGI_APPLICATION, path, headers, input_queue, output)
