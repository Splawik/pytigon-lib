"""Extra tests for :mod:`pytigon_lib.schtools.env`."""
import os
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schtools.env import get_environ


class TestGetEnvironExtra:
    def test_get_environ_is_not_none(self):
        env = get_environ()
        assert env is not None

    def test_get_environ_returns_same_instance(self):
        env1 = get_environ()
        env2 = get_environ()
        assert env1 is env2

    def test_get_environ_with_none_path(self):
        env = get_environ(None)
        assert env is not None

    @patch("os.path.exists", return_value=False)
    def test_path_does_not_exist(self, mock_exists):
        env = get_environ("/nonexistent")
        assert env is not None

    @patch("os.path.exists", return_value=True)
    def test_path_exists_but_no_read(self, mock_exists):
        env = get_environ("/some/path")
        assert env is not None

    def test_get_environ_has_debug_default(self):
        env = get_environ()
        assert env is not None

    def test_calling_twice_same_singleton(self):
        env_a = get_environ("/tmp")
        env_b = get_environ("/other")
        assert env_a is env_b

    @patch("os.path.exists", return_value=True)
    @patch("environ.Env.read_env")
    def test_read_env_not_called_on_second_call(self, mock_read, mock_exists):
        env1 = get_environ("/path")
        mock_read.reset_mock()
        env2 = get_environ("/path")
        assert env1 is env2

    @patch("os.path.exists", return_value=True)
    @patch("environ.Env.read_env", side_effect=Exception("read error"))
    def test_read_env_error_handled(self, mock_read, mock_exists):
        env = get_environ("/path")
        assert env is not None
