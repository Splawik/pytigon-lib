"""Tests for :mod:`pytigon_lib.schtools.process`."""
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schtools.process import FrozenModules, py_run, run


class TestFrozenModules:
    def test_init_and_restore(self):
        frozen = FrozenModules()
        try:
            assert frozen.original_keys is not None
        finally:
            frozen.restore()

    def test_restore_cleans_new_modules(self):
        frozen = FrozenModules()
        key_count_before = len(sys.modules)
        sys.modules["_test_fake_module_for_frozen"] = MagicMock()
        frozen.restore()
        assert "_test_fake_module_for_frozen" not in sys.modules


class TestRun:
    def test_run_returns_tuple(self):
        exit_code, stdout, stderr = run(["echo", "hello"])
        assert isinstance(exit_code, int)
        assert exit_code == 0

    @patch("subprocess.Popen")
    def test_run_handles_exception(self, mock_popen):
        mock_popen.side_effect = OSError("command not found")

        exit_code, stdout, stderr = run(["nonexistent_command"])
        assert exit_code == -1
        assert stdout is None
        assert stderr is None


class TestPyRun:
    @patch("pytigon_lib.schtools.process.run")
    def test_py_run_prepends_executable(self, mock_run):
        mock_run.return_value = (0, [], [])
        py_run(["script.py"])
        assert mock_run.called
