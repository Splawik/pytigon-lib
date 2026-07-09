"""Tests for :mod:`pytigon_lib.schtools.href_action`."""

import pytest

from pytigon_lib.schtools.href_action import (
    STANDARD_ACTIONS,
    get_action_parm,
    get_perm,
    unpack_value,
)


class TestStandardActions:
    def test_has_default_action(self):
        assert "default" in STANDARD_ACTIONS

    def test_has_edit_action(self):
        assert "edit" in STANDARD_ACTIONS

    def test_has_delete_action(self):
        assert "delete" in STANDARD_ACTIONS

    def test_default_has_target(self):
        assert "target" in STANDARD_ACTIONS["default"]

    def test_edit_has_url(self):
        assert "url" in STANDARD_ACTIONS["edit"]

    def test_all_targets_are_strings(self):
        for name, params in STANDARD_ACTIONS.items():
            if "target" in params:
                assert isinstance(params["target"], str), f"target for {name} is not str"


class TestUnpackValue:
    def test_empty_returns_empty(self):
        assert unpack_value(True, "") == ""

    def test_none_returns_empty(self):
        assert unpack_value(True, None) == ""

    def test_none_string_returns_empty(self):
        assert unpack_value(True, "None") == ""

    def test_plain_string(self):
        assert unpack_value(True, "hello") == "hello"

    def test_bracket_first_web(self):
        result = unpack_value(True, "[web_value|mobile_value]")
        assert result == "web_value"

    def test_bracket_first_mobile(self):
        result = unpack_value(False, "[web_value|mobile_value]")
        assert result == "mobile_value"

    def test_bracket_single_value(self):
        result = unpack_value(False, "[only_value]")
        assert result == "only_value"

    def test_bracket_single_value_web(self):
        result = unpack_value(True, "[only_value]")
        assert result == "only_value"

    def test_strips_whitespace(self):
        assert unpack_value(True, "  hello  ") == "hello"

    def test_bracket_with_pipe_in_value(self):
        result = unpack_value(True, "[class1 class2|class3 class4]")
        assert result == "class1 class2"


class TestGetActionParm:
    def test_known_action_target(self):
        result = get_action_parm(True, "edit", "target")
        assert result is not None

    def test_known_action_class(self):
        result = get_action_parm(True, "edit", "class")
        assert result is not None

    def test_unknown_key_returns_default(self):
        result = get_action_parm(True, "edit", "nonexistent_key", "default_val")
        assert result == "default_val"

    def test_default_action_key(self):
        result = get_action_parm(True, "edit", "target")
        assert result == "popup_edit"

    def test_action_not_in_standard_actions(self):
        result = get_action_parm(True, "unknown_action_xyz", "target", "fallback")
        assert result == "fallback" or result in ["_parent", "fallback"]

    def test_delete_action(self):
        result = get_action_parm(True, "delete", "target")
        assert result == "popup_delete"

    def test_new_row_action(self):
        result = get_action_parm(True, "new_row", "target")
        assert result == "popup_edit"

    def test_key_not_in_action_falls_to_default(self):
        result = get_action_parm(True, "back", "class")
        assert "btn" in result

    def test_composite_action_falls_back(self):
        result = get_action_parm(True, "edit-new_row", "target")
        assert result in ("popup_edit",)

    def test_icon_for_edit(self):
        result = get_action_parm(True, "edit", "icon")
        assert "fa-pencil" in result

    def test_icon_for_delete(self):
        result = get_action_parm(True, "delete", "icon")
        assert "fa-trash" in result


class TestGetPerm:
    def test_edit_permission(self):
        result = get_perm("myapp", "mymodel", "edit")
        assert "change" in result

    def test_delete_permission(self):
        result = get_perm("myapp", "mymodel", "delete")
        assert "delete" in result

    def test_other_action_returns_empty(self):
        result = get_perm("myapp", "mymodel", "view")
        assert result == ""

    def test_edit_in_action_name(self):
        result = get_perm("myapp", "mymodel", "action_edit")
        assert "change" in result

    def test_delete_in_action_name(self):
        result = get_perm("myapp", "mymodel", "action_delete")
        assert "delete" in result

    def test_permission_format(self):
        result = get_perm("app", "table", "edit")
        assert result == "app.change_table"

    def test_permission_format_delete(self):
        result = get_perm("app", "table", "delete")
        assert result == "app.delete_table"
