from pytigon_lib.schviews.tree import *

# Pytest tests
import pytest
from unittest.mock import MagicMock


@pytest.fixture
def mock_model():
    model = MagicMock()
    model.objects.filter.return_value = []
    return model


@pytest.fixture
def mock_callback():
    def callback(id, obj):
        if id == 0:
            return False
        elif id == 1:
            return "Test Node"
        elif id == 2:
            return [("link1", "Action 1"), ("link2", "Action 2")]

    return callback


def test_MakeTreeFromObject_init(mock_model, mock_callback):
    tree = MakeTreeFromObject(mock_model, mock_callback, "Test Field")
    assert tree.model == mock_model
    assert tree.callback == mock_callback
    assert tree.field_name == "Test Field"


def test_gen_html(mock_model, mock_callback):
    tree = MakeTreeFromObject(mock_model, mock_callback)
    html = tree.gen_html()
    assert html == "<ul id='browser' class='filetree'></ul>"


def test_gen_shtml(mock_model, mock_callback):
    tree = MakeTreeFromObject(mock_model, mock_callback)
    shtml = tree.gen_shtml()
    assert shtml == ""
