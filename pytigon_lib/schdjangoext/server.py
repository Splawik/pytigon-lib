"""Django-channels-based server management.

Provides utilities for starting and stopping a Django-channels
server (via Daphne/Granian) or a WSGI server (via Granian/Daphne)
in a subprocess.
"""

import datetime
import logging
import multiprocessing
import socket
import time

import django

_logger = logging.getLogger(__name__)


def log_action(protocol, action, details):
    """Log HTTP and WebSocket actions.

    This is the ``action_logger`` callback handed to the Daphne server, so it
    goes through :mod:`logging` rather than writing straight to stderr: stderr
    bypasses the project's log configuration entirely.

    Args:
        protocol: ``"http"`` or ``"websocket"``.
        action: ``"complete"``, ``"connected"``, or ``"disconnected"``.
        details: Dictionary with keys expected for the action type
            (e.g. ``method``, ``path``, ``status``, ``time_taken``,
            ``client``).
    """
    timestamp = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    try:
        if protocol == "http" and action == "complete":
            _logger.info(
                "[%s] HTTP %s %s %s [%.2f, %s]",
                timestamp,
                details.get("method", "?"),
                details.get("path", "?"),
                details.get("status", "?"),
                details.get("time_taken", 0),
                details.get("client", "?"),
            )
        elif protocol == "websocket" and action == "connected":
            _logger.info(
                "[%s] WebSocket CONNECT %s [%s]",
                timestamp,
                details.get("path", "?"),
                details.get("client", "?"),
            )
        elif protocol == "websocket" and action == "disconnected":
            _logger.info(
                "[%s] WebSocket DISCONNECT %s [%s]",
                timestamp,
                details.get("path", "?"),
                details.get("client", "?"),
            )
    except Exception:
        _logger.exception(
            "Unrecognized: protocol=%s action=%s details=%s", protocol, action, details
        )


def _run(addr, port, prod, params=None):
    """Internal function to run the server in a subprocess.

    Args:
        addr: Bind address.
        port: TCP port.
        prod: If True, use production server profile.
        params: Optional dict; may contain ``"wsgi"`` to use Granian
            (WSGI interface) instead of Daphne (ASGI interface).
    """
    try:
        if params and "wsgi" in params:
            use_granian = True
            try:
                from granian import Granian
            except ImportError:
                use_granian = False
            if use_granian:
                django.setup()
                Granian(
                    "wsgi:application",
                    interface="wsgi",
                    address=addr,
                    port=int(port),
                ).serve()
            else:
                from channels.routing import get_default_application
                from daphne.endpoints import build_endpoint_description_strings
                from daphne.server import Server

                django.setup()
                endpoints = build_endpoint_description_strings(host=addr, port=int(port))
                server = Server(
                    get_default_application(),
                    endpoints=endpoints,
                    signal_handlers=False,
                    action_logger=log_action,
                    http_timeout=60,
                )
                server.run()
        else:
            use_granian = True
            try:
                from granian import Granian
            except ImportError:
                use_granian = False
            if use_granian:
                from channels.routing import get_default_application

                django.setup()
                Granian(
                    get_default_application(),
                    interface="asgi",
                    address=addr,
                    port=int(port),
                ).serve()
            else:
                from channels.routing import get_default_application
                from daphne.endpoints import build_endpoint_description_strings
                from daphne.server import Server

                django.setup()
                endpoints = build_endpoint_description_strings(host=addr, port=int(port))
                server = Server(
                    get_default_application(),
                    endpoints=endpoints,
                    signal_handlers=False,
                    action_logger=log_action,
                    http_timeout=60,
                )
                server.run()
    except KeyboardInterrupt:
        return
    except Exception:
        _logger.exception("Error starting server")
        raise


class ServProc:
    """Wrapper around a :class:`multiprocessing.Process` for managing
    the server lifecycle."""

    def __init__(self, proc):
        """Initialize with a running process.

        Args:
            proc: A :class:`multiprocessing.Process` instance.
        """
        self.proc = proc

    def stop(self):
        """Terminate the server process."""
        self.proc.terminate()


def run_server(address, port, prod=True, params=None):
    """Start a Django-channels (or WSGI) server in a subprocess.

    Spawns a new process that runs the server and blocks until the
    socket is accepting connections.

    Args:
        address: Address to bind the HTTP server.
        port: TCP/IP port on which the server will listen.
        prod: If True, start in production mode; otherwise
            development mode.
        params: Additional parameters forwarded to :func:`_run`.

    Returns:
        ServProc: Handle for managing the server process.
    """
    _logger.info("Starting server: %s:%s", address, port)

    proc = multiprocessing.Process(target=_run, args=(address, port, prod, params))
    proc.start()

    # Wait until the server is up and running
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((address, port))
            break
        except (OSError, ConnectionRefusedError):
            time.sleep(0.1)

    _logger.info("Server started")
    return ServProc(proc)
