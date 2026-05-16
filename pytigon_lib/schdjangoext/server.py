"""Django-channels-based server management.

Provides utilities for starting and stopping a Django-channels
server (via Daphne) or a WSGI server (via Waitress) in a subprocess.
"""

import datetime
import multiprocessing
import socket
import sys
import time

import django


def log_action(protocol, action, details):
    """Log HTTP and WebSocket actions to stderr.

    Args:
        protocol: ``"http"`` or ``"websocket"``.
        action: ``"complete"``, ``"connected"``, or ``"disconnected"``.
        details: Dictionary with keys expected for the action type
            (e.g. ``method``, ``path``, ``status``, ``time_taken``,
            ``client``).
    """
    timestamp = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    msg = f"[{timestamp}] "

    try:
        if protocol == "http" and action == "complete":
            msg += (
                f"HTTP {details.get('method', '?')} "
                f"{details.get('path', '?')} "
                f"{details.get('status', '?')} "
                f"[{details.get('time_taken', 0):.2f}, {details.get('client', '?')}]\n"
            )
        elif protocol == "websocket" and action == "connected":
            msg += (
                f"WebSocket CONNECT {details.get('path', '?')} "
                f"[{details.get('client', '?')}]\n"
            )
        elif protocol == "websocket" and action == "disconnected":
            msg += (
                f"WebSocket DISCONNECT {details.get('path', '?')} "
                f"[{details.get('client', '?')}]\n"
            )
    except Exception:
        msg += f"Unrecognized: protocol={protocol} action={action} details={details}\n"

    sys.stderr.write(msg)


def _run(addr, port, prod, params=None):
    """Internal function to run the server in a subprocess.

    Args:
        addr: Bind address.
        port: TCP port.
        prod: If True, use production server profile.
        params: Optional dict; may contain ``"wsgi"`` to use Waitress
            instead of Daphne.
    """
    try:
        if params and "wsgi" in params:
            from waitress.runner import run

            django.setup()
            run(["embeded", f"--listen={addr}:{port}", "wsgi:application"])
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
    except Exception as e:
        sys.stderr.write(f"Error starting server: {e}\n")
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
    print(f"Starting server: {address}:{port}")

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

    print("Server started")
    return ServProc(proc)
