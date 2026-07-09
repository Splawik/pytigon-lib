"""Extra tests for :mod:`pytigon_lib.schtools.platform_info`."""
from unittest.mock import patch

import pytest

from pytigon_lib.schtools.platform_info import platform_name


class TestPlatformNameExtra:
    def test_returns_string(self):
        result = platform_name()
        assert isinstance(result, str)
        assert len(result) > 0

    @patch("pytigon_lib.schtools.platform_info.platform.system")
    @patch.dict("pytigon_lib.schtools.platform_info.environ", {}, clear=True)
    def test_linux_without_android(self, mock_system):
        mock_system.return_value = "Linux"
        assert platform_name() == "Linux"

    @patch("pytigon_lib.schtools.platform_info.platform.system")
    @patch.dict("pytigon_lib.schtools.platform_info.environ", {"ANDROID_ARGUMENT": "value"}, clear=True)
    def test_linux_with_android(self, mock_system):
        mock_system.return_value = "Linux"
        assert platform_name() == "Android"

    @patch("pytigon_lib.schtools.platform_info.platform.system")
    @patch.dict("pytigon_lib.schtools.platform_info.environ", {}, clear=True)
    def test_windows(self, mock_system):
        mock_system.return_value = "Windows"
        assert platform_name() == "Windows"

    @patch("pytigon_lib.schtools.platform_info.platform.system")
    @patch.dict("pytigon_lib.schtools.platform_info.environ", {}, clear=True)
    def test_darwin(self, mock_system):
        mock_system.return_value = "Darwin"
        assert platform_name() == "Darwin"

    @patch("pytigon_lib.schtools.platform_info.platform.system")
    @patch.dict("pytigon_lib.schtools.platform_info.environ", {}, clear=True)
    def test_error_returns_unknown(self, mock_system):
        mock_system.side_effect = Exception("system error")
        assert platform_name() == "Unknown"

    @patch("pytigon_lib.schtools.platform_info.platform.system")
    @patch.dict("pytigon_lib.schtools.platform_info.environ", {}, clear=True)
    def test_empty_system(self, mock_system):
        mock_system.return_value = ""
        result = platform_name()
        assert isinstance(result, str)
