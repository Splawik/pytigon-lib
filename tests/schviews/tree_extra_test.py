from unittest.mock import MagicMock

import pytest

from pytigon_lib.schviews.tree import _LI_END, _UL_END, MakeTreeFromObject


@pytest.fixture
def mock_model():
    model = MagicMock()
    model.objects.filter.return_value = MagicMock()
    return model


def callback_no_children(qid, obj):
    if qid == 0:
        return False
    elif qid == 1:
        return "Test Node"
    elif qid == 2:
        return []


def callback_with_children(qid, obj):
    if qid == 0:
        return True
    elif qid == 1:
        return "Folder Node"
    elif qid == 2:
        return [("/edit/1", "Edit"), ("/delete/1", "Delete")]


class TestMakeTreeFromObjectInit:
    def test_default_field_name_none(self, mock_model):
        tree = MakeTreeFromObject(mock_model, callback_no_children)
        assert tree.field_name is None
        assert tree.model is mock_model
        assert tree.callback is callback_no_children

    def test_field_name_set(self, mock_model):
        tree = MakeTreeFromObject(mock_model, callback_no_children, field_name="My Root")
        assert tree.field_name == "My Root"


class TestBuildNodeHtml:
    def test_simple_node_without_actions(self):
        html = MakeTreeFromObject._build_node_html("Label", [], "")
        assert "<li>" in html
        assert "Label" in html
        assert _LI_END in html

    def test_node_with_actions(self):
        actions = [("/link1", "Action1"), ("/link2", "Action2")]
        html = MakeTreeFromObject._build_node_html("Label", actions, "")
        assert "/link1" in html
        assert "/link2" in html
        assert "Action1" in html
        assert "Action2" in html

    def test_node_with_children_html(self):
        children = "<li><span>child</span></li>"
        html = MakeTreeFromObject._build_node_html("Label", [], children)
        assert children in html

    def test_escapes_action_names(self):
        actions = [("/link", 'Alert "XSS"')]
        html = MakeTreeFromObject._build_node_html("Label", actions, "")
        assert "&quot;" in html and "XSS" in html

    def test_escapes_action_links(self):
        actions = [('/path?x="evil"', "Name")]
        html = MakeTreeFromObject._build_node_html("Label", actions, "")
        assert "&quot;" in html and "evil" in html

    def test_folder_span_class(self):
        html = MakeTreeFromObject._build_node_html("Label", [], "")
        assert "class='folder'" in html

    def test_file_span_class(self):
        actions = [("/link", "Action")]
        html = MakeTreeFromObject._build_node_html("Label", actions, "")
        assert "class='file'" in html


class TestGenHtml:
    def test_empty_tree_no_field_name(self, mock_model):
        mock_model.objects.filter.return_value = []
        tree = MakeTreeFromObject(mock_model, callback_no_children)
        html = tree.gen_html()
        assert "<ul id='browser' class='filetree'>" in html
        assert html.endswith("</ul>")

    def test_empty_tree_with_field_name(self, mock_model):
        mock_model.objects.filter.return_value = []
        tree = MakeTreeFromObject(mock_model, callback_no_children, field_name="Root")
        html = tree.gen_html()
        assert "Root" in html

    def test_gen_shtml_no_wrappers(self, mock_model):
        mock_model.objects.filter.return_value = []
        tree = MakeTreeFromObject(mock_model, callback_no_children)
        html = tree.gen_shtml()
        assert "<ul id='browser'" not in html


class TestTreeFromObjectQueryError:
    def test_root_nodes_query_error_returns_empty(self, mock_model):
        mock_model.objects.filter.side_effect = RuntimeError("db error")
        tree = MakeTreeFromObject(mock_model, callback_no_children)
        html = tree.gen_html()
        assert html == "<ul id='browser' class='filetree'></ul>"


class TestUtils:
    def test_constants_non_empty(self):
        assert len(_UL_END) > 0
        assert len(_LI_END) > 0
        assert _UL_END == "</ul>"
        assert _LI_END == "</li>"
