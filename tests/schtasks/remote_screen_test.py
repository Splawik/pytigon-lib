import logging
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schtasks.remote_screen import (
    OnlyTxtParser,
    RemoteScreen,
    to_txt,
)


class TestOnlyTxtParser:
    def test_init_empty_txt(self):
        parser = OnlyTxtParser()
        assert parser.txt == []

    def test_single_data_element(self):
        parser = OnlyTxtParser()
        parser.handle_data("hello")
        assert parser.txt == ["hello"]

    def test_multiple_data_elements(self):
        parser = OnlyTxtParser()
        parser.handle_data("hello")
        parser.handle_data("world")
        assert parser.txt == ["hello", "world"]

    def test_strips_whitespace(self):
        parser = OnlyTxtParser()
        parser.handle_data("  hello  ")
        assert parser.txt == ["hello"]

    def test_to_txt_joins_with_space(self):
        parser = OnlyTxtParser()
        parser.handle_data("hello")
        parser.handle_data("world")
        assert parser.to_txt() == "hello world"

    def test_empty_to_txt(self):
        parser = OnlyTxtParser()
        assert parser.to_txt() == ""


class TestToTxt:
    def test_simple_html(self):
        result = to_txt("<p>Hello</p>")
        assert result == "Hello"

    def test_html_with_nested_tags(self):
        result = to_txt("<div><p>Hello <b>World</b></p></div>")
        assert result == "Hello World"

    def test_empty_html(self):
        result = to_txt("")
        assert result == ""

    def test_html_with_entities(self):
        result = to_txt("<p>&amp; &lt;</p>")
        assert "&amp;" in result or "&" in result

    def test_exception_returns_empty_string(self):
        with patch("pytigon_lib.schtasks.remote_screen.OnlyTxtParser") as mock_parser:
            mock_parser.return_value.feed.side_effect = Exception("parse error")
            result = to_txt("<p>bad</p>")
            assert result == ""


class TestRemoteScreen:
    def test_init_default_values(self):
        screen = RemoteScreen()
        assert screen.cproxy is None
        assert screen.direction == "down"

    def test_init_with_cproxy(self):
        proxy = MagicMock()
        screen = RemoteScreen(cproxy=proxy)
        assert screen.cproxy is proxy

    def test_context_manager_calls_raw_print_on_enter(self):
        screen = RemoteScreen()
        screen.raw_print = MagicMock()
        with screen:
            pass
        screen.raw_print.assert_called_once_with("<div class='log'></div>===>>")

    def test_context_manager_pass_on_exit(self):
        screen = RemoteScreen()
        with screen:
            pass

    def test_raw_print_without_cproxy_prints(self):
        screen = RemoteScreen()
        with patch("builtins.print") as mock_print:
            screen.raw_print("test message")
            mock_print.assert_called_once_with("test message")

    def test_raw_print_with_cproxy_sends_event(self):
        proxy = MagicMock()
        screen = RemoteScreen(cproxy=proxy)
        screen.raw_print("test message")
        proxy.send_event.assert_called_once_with("test message")

    def test_log_calls_internal_log(self):
        screen = RemoteScreen()
        screen._log = MagicMock()
        screen.log("message")
        screen._log.assert_called_once_with(
            "message", "log-line", logging.info, "===>>.log"
        )

    def test_info_calls_internal_log(self):
        screen = RemoteScreen()
        screen._log = MagicMock()
        screen.info("info message")
        screen._log.assert_called_once_with(
            "info message", "text-info", logging.info, "===>>.log"
        )

    def test_warning_calls_internal_log(self):
        screen = RemoteScreen()
        screen._log = MagicMock()
        screen.warning("warn message")
        screen._log.assert_called_once_with(
            "warn message", "text-warning", logging.warning, "===>>.log"
        )

    def test_error_calls_internal_log(self):
        screen = RemoteScreen()
        screen._log = MagicMock()
        screen.error("error message")
        screen._log.assert_called_once_with(
            "error message", "text-white bg-danger", logging.error, "===>>.log"
        )
