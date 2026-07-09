"""Tests for :mod:`pytigon_lib.schtools.env`."""
import pytest

from pytigon_lib.schtools.env import get_environ


class TestGetEnviron:
    def test_get_environ_returns_instance(self):
        env = get_environ()
        assert env is not None

    def test_get_environ_is_singleton(self):
        env1 = get_environ()
        env2 = get_environ()
        assert env1 is env2

    def test_get_environ_with_nonexistent_path(self):
        env = get_environ("/nonexistent/path")
        assert env is not None
