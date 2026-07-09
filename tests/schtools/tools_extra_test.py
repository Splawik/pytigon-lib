"""Additional tests for :mod:`pytigon_lib.schtools.tools` beyond tools_test.py and tools_extended_test.py."""

import inspect
import os
import types
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schtools.tools import (
    extend_fun_to,
    get_executable,
    get_from_dicts,
    get_request,
    get_session,
    is_in_dicts,
    is_null,
    bencode,
    bdecode,
    norm_indent,
    update_nested_dict,
)


class TestGetRequest:
    def test_no_request_found_returns_none(self):
        with patch("inspect.stack", return_value=[]):
            assert get_request() is None

    def test_request_with_session_attribute(self):
        mock_request = MagicMock()
        mock_request.session = MagicMock()

        frame = MagicMock()
        frame.f_code.co_varnames = ("request",)
        frame.f_locals = {"request": mock_request}

        frame_info = MagicMock()
        frame_info.frame = frame

        with patch("inspect.stack", return_value=[MagicMock(), frame_info]):
            result = get_request()
            assert result is mock_request

    def test_request_with_self_request_varnames(self):
        mock_request = MagicMock()
        mock_request.session = MagicMock()

        frame = MagicMock()
        frame.f_code.co_varnames = ("self", "request")
        frame.f_locals = {"request": mock_request}

        frame_info = MagicMock()
        frame_info.frame = frame

        with patch("inspect.stack", return_value=[MagicMock(), frame_info]):
            result = get_request()
            assert result is mock_request

    def test_request_skips_frame_without_session(self):
        mock_request = MagicMock()
        del mock_request.session

        frame = MagicMock()
        frame.f_code.co_varnames = ("request",)
        frame.f_locals = {"request": mock_request}

        frame_info = MagicMock()
        frame_info.frame = frame

        with patch("inspect.stack", return_value=[MagicMock(), frame_info]):
            assert get_request() is None


class TestGetSession:
    def test_get_session_returns_none_when_no_request(self):
        with patch("pytigon_lib.schtools.tools.get_request", return_value=None):
            assert get_session() is None

    def test_get_session_returns_session(self):
        mock_request = MagicMock()
        mock_request.session = {"user_id": 1}
        with patch("pytigon_lib.schtools.tools.get_request", return_value=mock_request):
            session = get_session()
            assert session == {"user_id": 1}


class TestIsInDicts:
    def test_generator_input(self):
        def gen():
            yield {"a": 1}
            yield {"b": 2}

        assert is_in_dicts("b", gen()) is True

    def test_set_of_dicts(self):
        dicts = [{"x": 1}, {"y": 2}]
        assert is_in_dicts("x", iter(dicts)) is True

    def test_false_with_none_elem(self):
        dicts = [{"a": 1}]
        assert is_in_dicts(None, dicts) is False


class TestGetFromDicts:
    def test_falsy_values_returned(self):
        dicts = [{"a": 0}, {"b": 2}]
        assert get_from_dicts("a", dicts) == 0

    def test_falsy_values_empty_list(self):
        dicts = [{"a": []}]
        assert get_from_dicts("a", dicts) == []

    def test_falsy_values_false(self):
        dicts = [{"a": False}]
        assert get_from_dicts("a", dicts) is False


class TestUpdateNestedDict:
    def test_non_dict_overwrites_nested(self):
        d = {"a": {"b": 1}}
        u = {"a": 42}
        update_nested_dict(d, u)
        assert d == {"a": 42}

    def test_new_nested_key_in_empty(self):
        d = {}
        u = {"a": {"b": 1}}
        update_nested_dict(d, u)
        assert d == {"a": {"b": 1}}


class TestExtendFunToExtra:
    def test_multiple_methods_on_same_object(self):
        obj = type("Multi", (), {})()

        @extend_fun_to(obj)
        def first(self):
            return 1

        @extend_fun_to(obj)
        def second(self):
            return 2

        assert obj.first() == 1
        assert obj.second() == 2

    def test_overwrite_existing_method(self):
        obj = type("Overwrite", (), {})()

        @extend_fun_to(obj)
        def greet(self):
            return "first"

        @extend_fun_to(obj)
        def greet(self):
            return "second"

        assert obj.greet() == "second"


class TestNormIndentExtra:
    def test_tabs_as_indent(self):
        text = "\tline1\n\tline2"
        assert norm_indent(text) == "line1\nline2"

    def test_mixed_indent_first_line_determines(self):
        text = "  line1\n\tline2"
        result = norm_indent(text)
        assert "line1" in result


class TestBencodeBdecodeExtra:
    def test_bencode_empty_string(self):
        assert bdecode(bencode("")) == ""

    def test_bencode_long_string(self):
        long_str = "x" * 1000
        assert bdecode(bencode(long_str)) == long_str

    def test_bdecode_invalid_raises(self):
        with pytest.raises(Exception):
            bdecode("!!!not-base64!!!")


class TestIsNullExtra:
    def test_is_null_with_object(self):
        obj = object()
        assert is_null(obj, "default") is obj
