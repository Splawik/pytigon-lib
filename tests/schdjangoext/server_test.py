import datetime
import multiprocessing
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schdjangoext.server import ServProc, log_action, run_server


class TestLogAction:
    def test_log_action_http_complete(self):
        details = {"method": "GET", "path": "/api/test", "status": "200", "time_taken": 0.123, "client": "127.0.0.1"}
        with patch.object(sys.stderr, "write") as mock_write:
            log_action("http", "complete", details)
            mock_write.assert_called_once()
            logged = mock_write.call_args[0][0]
            assert "HTTP GET" in logged
            assert "/api/test" in logged
            assert "200" in logged
            assert "0.12" in logged

    def test_log_action_websocket_connected(self):
        details = {"path": "/ws/chat", "client": "127.0.0.1"}
        with patch.object(sys.stderr, "write") as mock_write:
            log_action("websocket", "connected", details)
            logged = mock_write.call_args[0][0]
            assert "WebSocket CONNECT" in logged
            assert "/ws/chat" in logged

    def test_log_action_websocket_disconnected(self):
        details = {"path": "/ws/chat", "client": "127.0.0.1"}
        with patch.object(sys.stderr, "write") as mock_write:
            log_action("websocket", "disconnected", details)
            logged = mock_write.call_args[0][0]
            assert "WebSocket DISCONNECT" in logged

    def test_log_action_unrecognized_fallback(self):
        details = {"custom": "data"}
        with patch.object(sys.stderr, "write") as mock_write:
            log_action("unknown", "action", details)
            mock_write.assert_called_once()

    def test_log_action_exception_handling(self):
        details = None
        with patch.object(sys.stderr, "write") as mock_write:
            log_action("http", "complete", details)
            logged = mock_write.call_args[0][0]
            assert "Unrecognized" in logged

    def test_log_action_timestamp_format(self):
        details = {"method": "GET", "path": "/", "status": "200", "time_taken": 0.0, "client": "-"}
        with patch.object(sys.stderr, "write") as mock_write:
            log_action("http", "complete", details)
            logged = mock_write.call_args[0][0]
            assert "[" in logged
            assert "]" in logged


class TestServProc:
    def test_init_stores_process(self):
        proc = MagicMock()
        sp = ServProc(proc)
        assert sp.proc is proc

    def test_stop_terminates(self):
        proc = MagicMock()
        sp = ServProc(proc)
        sp.stop()
        proc.terminate.assert_called_once()


class TestRunServer:
    def test_run_server_starts_process(self):
        with patch("multiprocessing.Process") as mock_process_cls:
            mock_proc = MagicMock()
            mock_process_cls.return_value = mock_proc

            with patch("socket.socket") as mock_socket:
                mock_sock = MagicMock()
                mock_socket.return_value.__enter__.return_value = mock_sock
                mock_sock.connect.return_value = None

                result = run_server("127.0.0.1", 8080)
                mock_process_cls.assert_called_once()
                mock_proc.start.assert_called_once()
                assert isinstance(result, ServProc)

    def test_run_server_retries_connection(self):
        with patch("multiprocessing.Process") as mock_process_cls:
            mock_proc = MagicMock()
            mock_process_cls.return_value = mock_proc

            with patch("socket.socket") as mock_socket:
                mock_sock = MagicMock()
                mock_socket.return_value.__enter__.return_value = mock_sock
                mock_sock.connect.side_effect = [ConnectionRefusedError, ConnectionRefusedError, None]

                result = run_server("127.0.0.1", 9090)
                assert mock_sock.connect.call_count >= 2
                assert isinstance(result, ServProc)

    def test_run_server_with_params(self):
        with patch("multiprocessing.Process") as mock_process_cls:
            mock_proc = MagicMock()
            mock_process_cls.return_value = mock_proc

            with patch("socket.socket") as mock_socket:
                mock_sock = MagicMock()
                mock_socket.return_value.__enter__.return_value = mock_sock
                mock_sock.connect.return_value = None

                result = run_server("0.0.0.0", 8000, prod=False, params={"wsgi": True})
                mock_process_cls.assert_called_once()
                assert isinstance(result, ServProc)
