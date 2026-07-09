"""Tests for :mod:`pytigon_lib.schtools.main_paths`."""
import os
from unittest.mock import patch

import pytest

from pytigon_lib.schtools.main_paths import (
    PRJ_NAME,
    get_main_paths,
    get_prj_name,
    get_python_version,
    if_not_in_env,
)


class TestIfNotInEnv:
    def test_returns_env_value_when_set(self):
        with patch.dict(os.environ, {"PYTIGON_TEST_KEY": "from_env"}):
            result = if_not_in_env("TEST_KEY", "default_val")
            assert result == "from_env"

    def test_returns_default_when_env_not_set(self):
        result = if_not_in_env("NON_EXISTENT_KEY_XXXX", "default_val")
        assert result == "default_val"


class TestGetPythonVersion:
    def test_returns_three_segments_by_default(self):
        version = get_python_version()
        parts = version.split(".")
        assert len(parts) == 3

    def test_returns_two_segments(self):
        version = get_python_version(2)
        parts = version.split(".")
        assert len(parts) == 2

    def test_returns_one_segment(self):
        version = get_python_version(1)
        parts = version.split(".")
        assert len(parts) == 1

    def test_result_is_string(self):
        assert isinstance(get_python_version(), str)


class TestGetPrjName:
    def test_get_prj_name_returns_str(self):
        result = get_prj_name()
        assert isinstance(result, str)


class TestGetMainPaths:
    def test_returns_dict_with_prj(self):
        result = get_main_paths("_test_project")
        assert isinstance(result, dict)

    def test_has_temp_path_with_prj(self):
        result = get_main_paths("_test_project")
        assert "TEMP_PATH" in result

    def test_has_platform_type_with_prj(self):
        result = get_main_paths("_test_project")
        assert "PLATFORM_TYPE" in result
        assert result["PLATFORM_TYPE"] in ("standard", "pytigon-lib", "webserver", "android")

    def test_with_data_path_env(self):
        with patch.dict(os.environ, {"DATA_PATH": "/custom/data"}):
            result = get_main_paths("test")
            assert "DATA_PATH" in result

    def test_with_pytigon_root_path_env(self):
        with patch.dict(os.environ, {"PYTIGON_ROOT_PATH": "/custom/root"}):
            result = get_main_paths("test")
            assert result["ROOT_PATH"] == "/custom/root"

    def test_prj_path_env_override(self):
        with patch.dict(os.environ, {"PYTIGON_PRJ_PATH": "/custom/prj"}):
            result = get_main_paths("test")
            assert "PRJ_PATH" in result

    def test_log_path_is_set(self):
        result = get_main_paths("_test_project")
        assert "LOG_PATH" in result

    def test_staticfiles_dirs_is_list(self):
        result = get_main_paths()
        assert isinstance(result["STATICFILES_DIRS"], list)

    def test_serw_path_is_tracked(self):
        result = get_main_paths("_test_project")
        assert "SERW_PATH" in result

    def test_with_prj_name_sets_media(self):
        result = get_main_paths("testproject")
        assert "MEDIA_PATH" in result
