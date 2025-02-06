"""Django channels based server"""

import sys
import socket
import datetime
import multiprocessing
import django

# from pytigon.schserw.schsys.initdjango import init_django


def log_action(protocol, action, details):
    """Log actions such as HTTP requests or WebSocket connections."""
    timestamp = datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    msg = f"[{timestamp}] "

    if protocol == "http" and action == "complete":
        msg += f"HTTP {details['method']} {details['path']} {details['status']} [{details['time_taken']:.2f}, {details['client']}]\n"
    elif protocol == "websocket" and action == "connected":
        msg += f"WebSocket CONNECT {details['path']} [{details['client']}]\n"
    elif protocol == "websocket" and action == "disconnected":
        msg += f"WebSocket DISCONNECT {details['path']} [{details['client']}]\n"

    sys.stderr.write(msg)


def _run(addr, port, prod, params=None):
    """Internal function to run the server."""
    try:
        if params and "wsgi" in params:
            from waitress.runner import run

            django.setup()
            run(["embeded", f"--listen={addr}:{port}", "wsgi:application"])
        else:
            from daphne.server import Server
            from daphne.endpoints import build_endpoint_description_strings
            from channels.routing import get_default_application

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
    """Wrapper class for managing server processes."""

    def __init__(self, proc):
        self.proc = proc

    def stop(self):
        """Stop the server process."""
        self.proc.terminate()


def run_server(address, port, prod=True, params=None):
    """Run Django channels server.

    Args:
        address (str): Address to bind the HTTP server.
        port (int): TCP/IP port on which the server will run.
        prod (bool): If True, start server in production mode. If False, run in development mode.
        params (dict): Additional parameters for server configuration.

    Returns:
        ServProc: An instance of ServProc to manage the server process.
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
        except (ConnectionRefusedError, socket.error):
            pass

    print("Server started")
    return ServProc(proc)
