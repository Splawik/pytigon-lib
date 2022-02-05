from io import BytesIO
from pytigon_lib.schhttptools.asgi_bridge import get_scope_and_content_http_post
from urllib.parse import urlparse
import urllib
import copy

ENVIRON = {
    "HTTP_ACCEPT": "*/*",
    "HTTP_HOST": "127.0.0.1:8000",
    "HTTP_USER_AGENT": "wsgi bridge",
    "REQUEST_METHOD": "GET",
    "SERVER_NAME": "127.0.0.1",
    "SERVER_PORT": "8000",
    "SERVER_PROTOCOL": "HTTP/1.1",
    "SERVER_SOFTWARE": "TestServer/1.0",
    "wsgi.errors": BytesIO(b""),
    "wsgi.input": BytesIO(b""),
    "wsgi.multiprocess": False,
    "wsgi.multithread": False,
    "wsgi.run_once": False,
    "wsgi.url_scheme": "http",
    "wsgi.version": (1, 0),
}


def get_or_post(application, path, headers, params={}, post=False):
    global ENVIRON

    response_status = []
    response_headers = []  # headers

    def write(data):
        print(data)

    def start_response(status, headers):
        nonlocal response_status, response_headers
        status = status.split(" ", 1)
        response_status.append((int(status[0]), status[1]))
        response_headers.append(dict(headers))
        return write

    if "?" in path:
        x = path.split("?", 1)
        path2 = x[0]
        query = x[1]
    else:
        path2 = path
        query = ""

    content = urllib.parse.urlencode(params)
    bcontent = content.encode("utf-8")

    # scope, content = get_scope_and_content_http_post(path, headers, params)

    environ = copy.deepcopy(ENVIRON)

    for pos in headers:
        environ[pos[0].decode("utf-8")] = pos[1].decode("utf-8")

    environ["REQUEST_METHOD"] = "POST" if post else "GET"
    if post:
        environ["CONTENT_TYPE"] = "application/x-www-form-urlencoded"
        environ["CONTENT_LENGTH"] = len(content)

    environ["PATH_INFO"] = path2
    environ["QUERY_STRING"] = query

    environ["HTTP_HOST"] = "127.0.0.2:8000"
    environ["HTTP_ACCEPT"] = "*/*"
    environ["SERVER_NAME"] = "127.0.0.2"
    environ["SERVER_PORT"] = "8000"
    environ["SERVER_PROTOCOL"] = "HTTP/1.1"
    environ["SERVER_SOFTWARE"] = "pytigon/1.0"

    environ["wsgi.errors"] = BytesIO(b"")
    environ["wsgi.input"] = BytesIO(bcontent)
    environ["wsgi.multiprocess"] = False
    environ["wsgi.multithread"] = False
    environ["wsgi.run_once"] = False
    environ["wsgi.url_scheme"] = "http"
    environ["wsgi.version"] = (1, 0)

    if "cookie" in environ:
        environ["HTTP_COOKIE"] = environ["cookie"]

    response_body = application(environ, start_response)

    if response_body.status_code == 302:
        ret = get_or_post(application, urlparse(response_body.url).path, headers)

        for key, value in ret["headers"].items():
            response_headers[0][key] = value

        return {
            "status": ret["status"],
            "headers": response_headers[0],
            "body": ret["body"],
        }

    else:
        merged_body = "".join((x.decode("utf-8") for x in response_body))

        if hasattr(response_body, "close"):
            response_body.close()

        return {
            "status": response_status[0],
            "headers": response_headers[0],
            "body": merged_body,
        }
