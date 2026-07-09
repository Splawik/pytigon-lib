"""Extended tests for :mod:`pytigon_lib.schtools.tools`."""
import pytest

from pytigon_lib.schtools.tools import *


class TestSplit2:
    def test_split_found(self):
        assert split2("hello world", " ") == ("hello", "world")

    def test_split_not_found(self):
        assert split2("hello world", "x") == ("hello world", "")

    def test_split_empty_string(self):
        assert split2("", " ") == ("", "")

    def test_split_at_start(self):
        assert split2("/home/user", "/") == ("", "home/user")

    def test_split_at_end(self):
        assert split2("file.txt", ".") == ("file", "txt")

    def test_split_multiple_chars_sep(self):
        assert split2("a::b::c", "::") == ("a", "b::c")


class TestExtendFunTo:
    def test_extends_object_with_method(self):
        obj = type("Target", (), {})()

        @extend_fun_to(obj)
        def hello(self, name):
            return f"Hello {name}"

        assert obj.hello("World") == "Hello World"

    def test_function_name_is_preserved(self):
        obj = type("Target", (), {})()

        @extend_fun_to(obj)
        def my_func(self):
            pass

        assert obj.my_func.__name__ == "my_func"


class TestBencodeBdecode:
    def test_bencode_str(self):
        assert bencode("hello") == "aGVsbG8="

    def test_bencode_bytes(self):
        assert bencode(b"hello") == "aGVsbG8="

    def test_bdecode_str(self):
        assert bdecode("aGVsbG8=") == "hello"

    def test_bdecode_bytes(self):
        assert bdecode(b"aGVsbG8=") == "hello"

    def test_roundtrip_unicode(self):
        original = "zażółć gęślą jaźń"
        assert bdecode(bencode(original)) == original

    def test_roundtrip_bytes(self):
        original = b"\x00\x01\x02"
        assert bdecode(bencode(original)) == original.decode("utf-8")


class TestCleanHref:
    def test_removes_newline(self):
        assert clean_href("http://example.com\n") == "http://example.com"

    def test_removes_whitespace(self):
        assert clean_href("  http://example.com  ") == "http://example.com"

    def test_removes_internal_newline(self):
        assert clean_href("http://example.com\n/path") == "http://example.com/path"


class TestIsNull:
    def test_returns_value_when_truthy(self):
        assert is_null("value", "default") == "value"
        assert is_null(1, 0) == 1
        assert is_null(True, False) is True

    def test_returns_default_when_null(self):
        assert is_null(None, "default") == "default"
        assert is_null(0, 42) == 42
        assert is_null("", "default") == "default"
        assert is_null([], "default") == "default"
        assert is_null(False, True) is True


class TestGetExecutable:
    def test_returns_current_executable(self):
        exe = get_executable()
        assert isinstance(exe, str)
        assert len(exe) > 0
        assert "python" in os.path.basename(exe.replace("\\", "/"))


class TestNormIndent:
    def test_basic_indent(self):
        text = "  line1\n  line2"
        assert norm_indent(text) == "line1\nline2"

    def test_nested_indent(self):
        text = "  line1\n  line2\n    line3"
        assert norm_indent(text) == "line1\nline2\n  line3"

    def test_empty_lines_at_start(self):
        text = "\n\n  content"
        assert norm_indent(text) == "\n\ncontent"

    def test_no_indent(self):
        text = "line1\nline2"
        assert norm_indent(text) == "line1\nline2"

    def test_list_input(self):
        lines = ["  line1", "  line2"]
        assert norm_indent(lines) == "line1\nline2"

    def test_carriage_return(self):
        text = "  line1\r\n  line2"
        assert norm_indent(text) == "line1\nline2"

    def test_all_empty_lines(self):
        assert norm_indent("\n\n") == "\n\n"


class TestIsInDicts:
    def test_key_found_in_first(self):
        dicts = [{"a": 1}, {"b": 2}]
        assert is_in_dicts("a", dicts) is True

    def test_key_found_in_second(self):
        dicts = [{"a": 1}, {"b": 2}]
        assert is_in_dicts("b", dicts) is True

    def test_key_not_found(self):
        dicts = [{"a": 1}, {"b": 2}]
        assert is_in_dicts("z", dicts) is False

    def test_empty_dicts(self):
        assert is_in_dicts("a", []) is False


class TestGetFromDicts:
    def test_gets_from_first(self):
        dicts = [{"a": 1}, {"a": 2}]
        assert get_from_dicts("a", dicts) == 1

    def test_gets_from_second(self):
        dicts = [{"a": 1}, {"b": 2}]
        assert get_from_dicts("b", dicts) == 2

    def test_key_not_found_returns_none(self):
        dicts = [{"a": 1}, {"b": 2}]
        assert get_from_dicts("z", dicts) is None

    def test_empty_dicts_returns_none(self):
        assert get_from_dicts("a", []) is None

    def test_none_values(self):
        dicts = [{"a": None}]
        assert get_from_dicts("a", dicts) is None


class TestUpdateNestedDict:
    def test_top_level_update(self):
        d = {"a": 1, "b": 2}
        u = {"b": 3, "c": 4}
        update_nested_dict(d, u)
        assert d == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        d = {"a": {"b": 1}}
        u = {"a": {"c": 2}}
        update_nested_dict(d, u)
        assert d == {"a": {"b": 1, "c": 2}}

    def test_nested_overwrite(self):
        d = {"a": {"b": 1, "c": 2}}
        u = {"a": {"c": 3}}
        update_nested_dict(d, u)
        assert d == {"a": {"b": 1, "c": 3}}

    def test_deep_nested(self):
        d = {"a": {"b": {"x": 1}}}
        u = {"a": {"b": {"y": 2}, "c": 3}}
        update_nested_dict(d, u)
        assert d == {"a": {"b": {"x": 1, "y": 2}, "c": 3}}

    def test_empty_update(self):
        d = {"a": 1}
        u = {}
        update_nested_dict(d, u)
        assert d == {"a": 1}

    def test_return_value(self):
        d = {"a": 1}
        u = {"b": 2}
        result = update_nested_dict(d, u)
        assert result is d
