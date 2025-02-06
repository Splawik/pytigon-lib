import urllib.parse
import copy
from typing import Dict, List, Tuple, Any, Optional

SCOPE_TEMPLATE = {
    "type": "http",
    "http_version": "1.1",
    "method": "GET",
    "path": "/",
    "root_path": "",
    "scheme": "http",
    "query_string": b"",
    "headers": [
        (b"host", b"127.0.0.2"),
        (b"user-agent", b"python-urllib3/0.6 asgi bridge"),
        (b"accept", b"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"),
        (b"accept-language", b"pl,en-US;q=0.7,en;q=0.3"),
        (b"accept-encoding", b"gzip, deflate"),
        (b"origin", b"http://127.0.0.2"),
        (b"connection", b"keep-alive"),
        (b"cache-control", b"max-age=0"),
    ],
    "client": ["127.0.0.2", 60748],
    "server": ["127.0.0.2", 80],
}


def get_scope_and_content_http_get(
    path: str, headers: List[Tuple[str, str]]
) -> Tuple[Dict[str, Any], str]:
    """Generate a scope and content for an HTTP GET request."""
    scope = copy.deepcopy(SCOPE_TEMPLATE)
    path2, query = (
        (path.split("?", 1)[0], path.split("?", 1)[1]) if "?" in path else (path, "")
    )

    scope["path"] = path2
    scope["query_string"] = query.encode("utf-8")

    for key, value in headers:
        key_bytes = key.encode("utf-8") if isinstance(key, str) else key
        scope["headers"] = [
            (k, v) for k, v in scope["headers"] if k.lower() != key_bytes.lower()
        ]
        scope["headers"].append((key_bytes, value))

    return scope, ""


def get_scope_and_content_http_post(
    path: str, headers: List[Tuple[str, str]], params: Optional[Dict[str, str]] = None
) -> Tuple[Dict[str, Any], str]:
    """Generate a scope and content for an HTTP POST request."""
    scope, content = get_scope_and_content_http_get(path, headers)
    scope["method"] = "POST"
    scope["headers"].extend(
        [
            (b"upgrade-insecure-requests", b"1"),
            (b"content-type", b"application/x-www-form-urlencoded"),
        ]
    )

    content = urllib.parse.urlencode(params) if params else ""
    scope["headers"].append((b"content-length", str(len(content)).encode("utf-8")))

    return scope, content


def get_scope_websocket(path: str, headers: List[Tuple[str, str]]) -> Dict[str, Any]:
    """Generate a scope for a WebSocket connection."""
    scope, _ = get_scope_and_content_http_get(path, headers)
    scope["type"] = "websocket"
    return scope


async def get_or_post(
    application,
    path: str,
    headers: List[Tuple[str, str]],
    params: Optional[Dict[str, str]] = None,
    post: bool = False,
) -> Dict[str, Any]:
    """Handle GET or POST requests and return the response."""
    ret = {}
    scope, content = (
        get_scope_and_content_http_post(path, headers, params)
        if post
        else get_scope_and_content_http_get(path, headers)
    )

    async def send(message: Dict[str, Any]) -> None:
        """Send a message to the client."""
        nonlocal ret
        for key, value in message.items():
            ret[key] = ret.get(key, "") + value

    async def receive() -> Dict[str, Any]:
        """Receive a message from the client."""
        nonlocal content
        return {"type": "http", "body": content.encode("utf-8")}

    await application(scope, receive, send)

    if ret.get("status") == 302 and "headers" in ret:
        for pos in ret["headers"]:
            if pos[0] == b"Location":
                new_url = pos[1].decode("utf-8").replace("http://127.0.0.2", "")
                ret2 = await get_or_post(application, new_url, headers)
                if "headers" in ret:
                    ret2["headers"].extend(ret["headers"])
                return ret2

    return ret


async def websocket(
    application, path: str, headers: List[Tuple[str, str]], input_queue, output
) -> Dict[str, Any]:
    """Handle WebSocket connections."""
    ret = {}
    scope = get_scope_websocket(path.replace("ws://127.0.0.2/", ""), headers)
    connected = False

    async def send(message: Dict[str, Any]) -> None:
        """Send a WebSocket message to the client."""
        if message["type"] == "websocket.accept":
            output.onOpen()
        elif message["type"] == "websocket.send":
            text = message.get("text")
            binary = message.get("binary")
            output.onMessage(text, binary)
        elif message["type"] == "websocket.disconnect":
            output.onClose(None, None, None)

    async def receive() -> Dict[str, Any]:
        """Receive a WebSocket message from the client."""
        nonlocal connected
        if not connected:
            connected = True
            return {"type": "websocket.connect"}
        item = await input_queue.get()
        return (
            {"type": "websocket.receive", "text": item}
            if item
            else {"type": "websocket.disconnect"}
        )

    await application(scope, receive, send)
    return ret
