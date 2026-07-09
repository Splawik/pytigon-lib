"""Tests for :mod:`pytigon_lib.schtools.createparm`."""
import pytest

from pytigon_lib.schtools.createparm import (
    DictParm,
    convert_param,
    create_parm,
    create_post_param,
    dict_from_param,
)


class TestDictParm:
    def test_init(self):
        d = DictParm({"a": 1, "b": 2})
        assert d.data == {"a": 1, "b": 2}

    def test_get_parm(self):
        d = DictParm({"a": 1, "b": 2})
        assert d.get_parm("a") == 1
        assert d.get_parm("b") == 2

    def test_get_parm_missing(self):
        d = DictParm({"a": 1})
        with pytest.raises(KeyError, match="not found"):
            d.get_parm("missing")

    def test_has_parm(self):
        d = DictParm({"a": 1})
        assert d.has_parm("a") is True
        assert d.has_parm("missing") is False


class TestConvertParam:
    def test_convert_str(self):
        result = convert_param(42)
        assert result == "42"

    def test_convert_bool(self):
        result = convert_param(True)
        assert result is True

    def test_convert_list(self):
        result = convert_param([1, 2, 3])
        assert result == [1, 2, 3]

    def test_convert_none(self):
        result = convert_param(None)
        assert result == "None"


class TestDictFromParam:
    def test_dict_from_param(self):
        d = DictParm({"a": 1, "b": 2, "c": 3})
        result = dict_from_param(d, ["a", "c"])
        assert result == {"a": 1, "c": 3}

    def test_dict_from_param_missing(self):
        d = DictParm({"a": 1})
        result = dict_from_param(d, ["a", "missing"])
        assert result == {"a": 1}

    def test_dict_from_param_empty(self):
        d = DictParm({})
        result = dict_from_param(d, ["a"])
        assert result == {}


class TestCreateParm:
    def test_create_parm_empty(self):
        result = create_parm("", DictParm({}))
        assert result is None

    def test_create_parm_no_pipe(self):
        result = create_parm("http://example.com", DictParm({"a": 1}))
        assert result is None

    def test_create_parm_basic(self):
        result = create_parm("http://example.com|a,b", DictParm({"a": 1, "b": 2}))
        assert result is not None
        base, sep, params = result
        assert base == "http://example.com"
        assert "a=1" in params
        assert "b=2" in params

    def test_create_parm_no_encode(self):
        result = create_parm("http://example.com|a,b", DictParm({"a": 1, "b": 2}), no_encode=True)
        assert result is not None
        base, sep, params = result
        assert params == {"a": "1", "b": "2"}

    def test_create_parm_missing_param(self):
        result = create_parm("http://example.com|a,b", DictParm({"a": 1}))
        base, sep, params = result
        assert "b" not in params

    def test_create_parm_none_value_skip(self):
        result = create_parm("http://example.com|a", DictParm({"a": None}))
        base, sep, params = result
        assert "a" not in params

    def test_create_parm_double_underscore(self):
        result = create_parm(
            "http://example.com|filter__date,filter__type",
            DictParm({"filter__date": "2023", "filter__type": "csv"}),
        )
        base, sep, params = result
        assert "filter" in params

    def test_create_parm_double_underscore_multiple_values(self):
        result = create_parm(
            "http://example.com|filter__a,filter__b",
            DictParm({"filter__a": "val1", "filter__b": "val2"}),
        )
        base, sep, params = result
        assert "filter=val1" in params or "filter" in params


class TestCreatePostParam:
    def test_create_post_param_basic(self):
        result = create_post_param("http://example.com|a,b", DictParm({"a": 1, "b": 2}))
        assert result[0] == "http://example.com"
        assert result[1] == {"a": 1, "b": 2}

    def test_create_post_param_no_pipe(self):
        result = create_post_param("http://example.com", DictParm({"a": 1}))
        assert result == ("http://example.com", {})
