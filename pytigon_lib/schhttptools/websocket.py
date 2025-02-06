import asyncio
from autobahn.twisted.websocket import (
    WebSocketClientFactory,
    WebSocketClientProtocol,
    connectWS,
)
from pytigon_lib.schtools.schjson import json_dumps, json_loads


class PytigonClientProtocolBase:
    """Base class for Pytigon WebSocket client protocol."""

    def onConnect(self, response):
        """Handle WebSocket connection."""
        return self.app.on_websocket_connect(self, self.websocket_id, response)

    def onOpen(self):
        """Handle WebSocket open event."""
        return self.app.on_websocket_open(self, self.websocket_id)

    def onClose(self, wasClean, code, reason):
        """Handle WebSocket close event."""
        pass

    def onMessage(self, msg, binary):
        """Handle incoming WebSocket message."""
        return self.app.on_websocket_message(self, self.websocket_id, {"msg": msg})


def create_websocket_client(app, websocket_id, local=False, callback=False):
    """Create a WebSocket client.

    Args:
        app: The application instance.
        websocket_id: The unique identifier for the WebSocket connection.
        local: If True, create a local WebSocket client.
        callback: Optional callback function to be added to the WebSocket.
    """
    if local:

        class PytigonClientProtocol(PytigonClientProtocolBase):
            """Local WebSocket client protocol."""

            def __init__(self, app):
                """Initialize the local WebSocket client."""
                self.app = app
                self.websocket_id = websocket_id
                self.input_queue = asyncio.Queue()
                self.callbacks = []
                self.status = 1

            async def send_message(self, msg):
                """Send a message through the WebSocket."""
                await self.input_queue.put(json_dumps(msg))

        app.websockets[websocket_id] = PytigonClientProtocol(app)

    else:

        class PytigonClientProtocol(PytigonClientProtocolBase, WebSocketClientProtocol):
            """Remote WebSocket client protocol."""

            def __init__(self):
                """Initialize the remote WebSocket client."""
                nonlocal app, websocket_id
                PytigonClientProtocolBase.__init__(self)
                WebSocketClientProtocol.__init__(self)
                self.app = app
                self.websocket_id = websocket_id
                app.websockets[websocket_id] = self
                self.status = 0

            def send_message(self, msg):
                """Send a message through the WebSocket."""
                try:
                    super().sendMessage(json_dumps(msg).encode("utf-8"))
                except Exception as e:
                    print(f"Failed to send message: {e}")

        ws_address = app.base_address.replace("http", "ws").replace("https", "wss")
        ws_address += websocket_id
        factory = WebSocketClientFactory(ws_address)
        factory.protocol = PytigonClientProtocol
        connectWS(factory)

    if callback:
        app.add_websoket_callback(websocket_id, callback)
