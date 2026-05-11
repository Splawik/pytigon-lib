"""WebSocket client implementation for Pytigon.

Provides both local (in-process via asyncio.Queue) and remote
(via autobahn/Twisted) WebSocket client protocols.
"""

import asyncio
import logging
from autobahn.twisted.websocket import (
    WebSocketClientFactory,
    WebSocketClientProtocol,
    connectWS,
)
from pytigon_lib.schtools.schjson import json_dumps, json_loads

LOGGER = logging.getLogger("pytigon.websocket")


class PytigonClientProtocolBase:
    """Base class for Pytigon WebSocket client protocol.

    Delegates WebSocket events to the application instance via
    on_websocket_connect, on_websocket_open, on_websocket_message callbacks.
    """

    def onConnect(self, response):
        """Handle WebSocket connection established."""
        return self.app.on_websocket_connect(self, self.websocket_id, response)

    def onOpen(self):
        """Handle WebSocket opened."""
        return self.app.on_websocket_open(self, self.websocket_id)

    def onClose(self, wasClean, code, reason):
        """Handle WebSocket closed.

        Note: The base implementation does nothing; override in subclasses
        or handle via application callbacks.
        """
        pass

    def onMessage(self, msg, binary):
        """Handle incoming WebSocket message."""
        return self.app.on_websocket_message(self, self.websocket_id, {"msg": msg})


def create_websocket_client(app, websocket_id, local=False, callback=False):
    """Create a WebSocket client and register it with the application.

    Args:
        app: The application instance (must have a 'websockets' dict and
            'base_address' attribute for remote connections).
        websocket_id: Unique identifier for the WebSocket connection.
        local: If True, create an in-process client using asyncio.Queue.
            If False, create a remote client using autobahn/Twisted.
        callback: Optional callback function to register on the WebSocket.
    """
    if local:

        class PytigonClientProtocol(PytigonClientProtocolBase):
            """Local (in-process) WebSocket client using asyncio.Queue."""

            def __init__(self, app):
                self.app = app
                self.websocket_id = websocket_id
                self.input_queue = asyncio.Queue()
                self.callbacks = []
                self.status = 1

            async def send_message(self, msg):
                """Enqueue a JSON-encoded message for the WebSocket bridge."""
                await self.input_queue.put(json_dumps(msg))

        app.websockets[websocket_id] = PytigonClientProtocol(app)

    else:

        class PytigonClientProtocol(PytigonClientProtocolBase, WebSocketClientProtocol):
            """Remote WebSocket client using autobahn/Twisted transport."""

            def __init__(self):
                nonlocal app, websocket_id
                PytigonClientProtocolBase.__init__(self)
                WebSocketClientProtocol.__init__(self)
                self.app = app
                self.websocket_id = websocket_id
                app.websockets[websocket_id] = self
                self.status = 0

            def send_message(self, msg):
                """Send a JSON-encoded message over the WebSocket."""
                try:
                    super().sendMessage(json_dumps(msg).encode("utf-8"))
                except Exception as e:
                    LOGGER.error("Failed to send WebSocket message: %s", e)

        ws_address = app.base_address.replace("http", "ws").replace("https", "wss")
        ws_address += websocket_id
        factory = WebSocketClientFactory(ws_address)
        factory.protocol = PytigonClientProtocol
        connectWS(factory)

    if callback:
        app.add_websoket_callback(websocket_id, callback)
