"""Tests for :mod:`pytigon_lib.schtools.platform_info`."""
import pytest

from pytigon_lib.schtools.platform_info import platform_name


class TestPlatformInfo:
    def test_platform_name_returns_str(self):
        name = platform_name()
        assert isinstance(name, str)
        assert len(name) > 0
