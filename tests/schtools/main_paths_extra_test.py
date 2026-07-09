"""Additional tests for :mod:`pytigon_lib.schtools.main_paths` beyond main_paths_test.py."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schtools.main_paths import (
    PRJ_NAME,
    get_main_paths,
    get_prj_name,
    get_python_version,
    if_not_in_env,
)


class TestIfNotInEnvExtra:
    def test_env_key_prefix_is_pytigon(self):
        with patch.dict(os.environ, {"PYTIGON_MYKEY": "val"}):
            assert if_not_in_env("MYKEY", "def") == "val"

    def test_default_with_none_value(self):
        result = if_not_in_env("NON_EXISTENT_XXX", None)
        assert result is None

    def test_default_empty_string(self):
        result = if_not_in_env("NON_EXISTENT_YYY", "")
        assert result == ""


class TestGetPythonVersionExtra:
    def test_zero_segments_returns_empty(self):
        version = get_python_version(0)
        assert version == ""

    def test_many_segments_returns_all(self):
        version = get_python_version(10)
        parts = version.split(".")
        assert len(parts) <= 3

    def test_version_starts_with_digit(self):
        version = get_python_version()
        assert version[0].isdigit()


class TestGetPrjNameExtra:
    def test_get_prj_name_after_setting(self):
        result = get_main_paths("testproject_123")
        assert get_prj_name() == "testproject_123"

    def test_get_prj_name_with_no_args(self):
        get_main_paths("temp_proj")
        assert get_prj_name() == "temp_proj"


class TestGetMainPathsExtra:
    def test_media_path_with_prj_name(self):
        result = get_main_paths("myprj")
        assert "MEDIA_PATH" in result
        assert "myprj" in result["MEDIA_PATH"]

    def test_media_path_protected_with_prj_name(self):
        result = get_main_paths("myprj")
        assert "MEDIA_PATH_PROTECTED" in result
        assert "myprj" in result["MEDIA_PATH_PROTECTED"]

    def test_upload_path_with_prj_name(self):
        result = get_main_paths("myprj")
        assert "UPLOAD_PATH" in result

    def test_upload_path_protected_with_prj_name(self):
        result = get_main_paths("myprj")
        assert "UPLOAD_PATH_PROTECTED" in result

    def test_static_path_with_prj_name_and_webserver_env(self):
        with patch.dict(
            os.environ,
            {
                "DATA_PATH": "/srv/data",
                "START_PATH": "/home/www-data/www/pytigon",
            },
            clear=True,
        ):
            result = get_main_paths("webprj")
            assert "STATIC_PATH" in result
            assert "webprj" in result["STATIC_PATH"]

    def test_pytigon_path_is_set(self):
        result = get_main_paths("testproj")
        assert "PYTIGON_PATH" in result

    def test_no_prj_name_sets_global(self):
        get_main_paths("test_global")
        assert get_prj_name() == "test_global"

    def test_without_prj_name_no_media_when_prj_name_is_cleared(self):
        result = get_main_paths()
        media_in = "MEDIA_PATH" in result
        assert media_in is (get_prj_name() != "")

    def test_platform_type_from_start_path(self):
        with patch.dict(os.environ, {"START_PATH": "/home/www-data/projects"}, clear=True):
            result = get_main_paths("test")
            assert result["PLATFORM_TYPE"] == "webserver"

    def test_android_secondary_storage(self):
        with patch.dict(
            os.environ,
            {"SECONDARY_STORAGE": "/mnt/sdcard"},
            clear=True,
        ):
            with patch("pytigon_lib.schtools.main_paths.platform_name", return_value="Android"):
                result = get_main_paths("test")
                assert result["DATA_PATH"].startswith("/mnt/sdcard")

    def test_android_external_storage(self):
        with patch.dict(
            os.environ,
            {"EXTERNAL_STORAGE": "/storage/emulated/0"},
            clear=True,
        ):
            with patch("pytigon_lib.schtools.main_paths.platform_name", return_value="Android"):
                result = get_main_paths("test")
                assert result["DATA_PATH"].startswith("/storage/emulated/0")

    def test_multiple_allowed_platform_types(self):
        result = get_main_paths("test")
        assert result["PLATFORM_TYPE"] in (
            "standard",
            "pytigon-lib",
            "webserver",
            "android",
        )

    def test_empty_prj_name(self):
        result = get_main_paths("")
        assert isinstance(result, dict)
        assert "TEMP_PATH" in result

    def test_static_path_env_override(self):
        with patch.dict(os.environ, {"STATIC_PATH": "/custom/static"}, clear=True):
            result = get_main_paths("test")
            assert result["STATIC_PATH"] == "/custom/static"
