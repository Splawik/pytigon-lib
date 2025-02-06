from pytigon_lib.schtools.createparm import *

# Pytest tests
import pytest


def test_dict_parm():
    data = {"key1": "value1", "key2": 42}
    parm = DictParm(data)
    assert parm.get_parm("key1") == "value1"
    assert parm.has_parm("key2")
    with pytest.raises(KeyError):
        parm.get_parm("nonexistent")


def test_convert_param():
    from datetime import datetime

    dt = datetime(2023, 10, 1)
    assert convert_param(dt) == "2023-10-01 00:00:00"
    assert convert_param([1, 2, 3]) == [1, 2, 3]
    assert convert_param(True) is True
    assert convert_param("test") == "test"


def test_dict_from_param():
    data = {"key1": "value1", "key2": 42}
    parm = DictParm(data)
    fields = ["key1", "key2"]
    result = dict_from_param(parm, fields)
    assert result == {"key1": "value1", "key2": 42}


def test_create_parm():
    data = {"key1": "value1", "key2": 42}
    parm = DictParm(data)
    address = "endpoint|key1,key2"
    result = create_parm(address, parm)
    assert result == ("endpoint", "?", "key1=value1&key2=42")


def test_create_post_param():
    data = {"key1": "value1", "key2": 42}
    parm = DictParm(data)
    address = "endpoint|key1,key2"
    result = create_post_param(address, parm)
    assert result == ("endpoint", {"key1": "value1", "key2": 42})
