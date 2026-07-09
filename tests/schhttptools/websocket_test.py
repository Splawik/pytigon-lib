import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pytigon_lib.schhttptools.websocket import (
    PytigonClientProtocolBase,
    create_websocket_client,
)


class TestPytigonClientProtocolBase:
    def test_on_connect_calls_app_callback(self):
        app = MagicMock()
        protocol = PytigonClientProtocolBase()
        protocol.app = app
        protocol.websocket_id = "ws-1"
        response = MagicMock()
        protocol.onConnect(response)
        app.on_websocket_connect.assert_called_once_with(protocol, "ws-1", response)

    def test_on_open_calls_app_callback(self):
        app = MagicMock()
        protocol = PytigonClientProtocolBase()
        protocol.app = app
        protocol.websocket_id = "ws-1"
        protocol.onOpen()
        app.on_websocket_open.assert_called_once_with(protocol, "ws-1")

    def test_on_close_is_no_op(self):
        protocol = PytigonClientProtocolBase()
        assert protocol.onClose(True, 1000, "normal") is None

    def test_on_message_calls_app_callback(self):
        app = MagicMock()
        protocol = PytigonClientProtocolBase()
        protocol.app = app
        protocol.websocket_id = "ws-1"
        protocol.onMessage("hello", False)
        app.on_websocket_message.assert_called_once_with(protocol, "ws-1", {"msg": "hello"})


class TestCreateWebsocketClientLocal:
    def test_creates_local_client_and_registers(self):
        app = MagicMock()
        app.websockets = {}
        create_websocket_client(app, "ws-local", local=True)
        assert "ws-local" in app.websockets
        protocol = app.websockets["ws-local"]
        assert protocol.status == 1

    def test_local_client_has_input_queue(self):
        app = MagicMock()
        app.websockets = {}
        create_websocket_client(app, "ws-local", local=True)
        protocol = app.websockets["ws-local"]
        assert isinstance(protocol.input_queue, asyncio.Queue)

    def test_local_client_has_callbacks(self):
        app = MagicMock()
        app.websockets = {}
        create_websocket_client(app, "ws-local", local=True)
        protocol = app.websockets["ws-local"]
        assert protocol.callbacks == []

    def test_creates_local_client_with_callback(self):
        app = MagicMock()
        app.websockets = {}
        app.add_websoket_callback = MagicMock()
        cb = MagicMock()
        create_websocket_client(app, "ws-local", local=True, callback=cb)
        app.add_websoket_callback.assert_called_once_with("ws-local", cb)

    def test_remote_client_factory_configured(self):
        with patch("pytigon_lib.schhttptools.websocket.connectWS") as mock_connect:
            with patch("pytigon_lib.schhttptools.websocket.WebSocketClientFactory") as mock_factory:
                app = MagicMock()
                app.websockets = {}
                app.base_address = "http://example.com"
                create_websocket_client(app, "ws-remote", local=False)
                expected_address = "ws://example.comws-remote"
                mock_factory.assert_called_once_with(expected_address)

    def test_remote_client_calls_connect_ws(self):
        with patch("pytigon_lib.schhttptools.websocket.connectWS") as mock_connect:
            with patch("pytigon_lib.schhttptools.websocket.WebSocketClientFactory"):
                app = MagicMock()
                app.websockets = {}
                app.base_address = "http://example.com"
                create_websocket_client(app, "ws-remote", local=False)
                mock_connect.assert_called_once()

    def test_no_callback_not_registered(self):
        app = MagicMock()
        app.websockets = {}
        create_websocket_client(app, "ws-test", local=True, callback=False)
        app.add_websoket_callback.assert_not_called()
