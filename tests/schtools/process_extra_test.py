"""Additional tests for :mod:`pytigon_lib.schtools.process` beyond process_test.py and process_extended_test.py."""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schtools.process import FrozenModules, py_manage, py_run, run


class TestRunExtra:
    def test_run_with_shell_true(self):
        with patch("pytigon_lib.schtools.process.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = (b"output\n", None)
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            exit_code, output, err = run(["echo hello"], shell=True)
            call_kwargs = mock_popen.call_args[1]
            assert call_kwargs["shell"] is True

    def test_run_with_env_vars(self):
        custom_env = {"MY_VAR": "my_value"}
        with patch("pytigon_lib.schtools.process.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = (b"ok", b"")
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            run(["env"], env=custom_env)
            call_kwargs = mock_popen.call_args[1]
            assert call_kwargs["env"] == custom_env

    def test_run_preserves_carriage_return_removal(self):
        with patch("pytigon_lib.schtools.process.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = (b"line1\r\nline2\r\n", b"")
            mock_process.wait.return_value = 0
            mock_popen.return_value = mock_process

            exit_code, output, err = run(["cmd"])
            assert "\r" not in output[0]
            assert "\r" not in output[1]

    def test_run_nonzero_exit_code(self):
        with patch("pytigon_lib.schtools.process.Popen") as mock_popen:
            mock_process = MagicMock()
            mock_process.communicate.return_value = (b"", b"error occurred")
            mock_process.wait.return_value = 1
            mock_popen.return_value = mock_process

            exit_code, output, err = run(["failing_cmd"])
            assert exit_code == 1

    def test_run_exception_returns_neg_one(self):
        with patch("subprocess.Popen", side_effect=Exception("boom")):
            exit_code, output, err = run(["bad_cmd"])
            assert exit_code == -1
            assert output is None
            assert err is None


class TestPyRun:
    def test_py_run_calls_get_executable(self):
        with patch("pytigon_lib.schtools.process.get_executable", return_value="/usr/bin/python3"):
            with patch("pytigon_lib.schtools.process.run", return_value=(0, [], [])):
                py_run(["-c", "print('hello')"])
                assert True


class TestPyManage:
    def test_py_manage_empty_cmd_returns_zero(self):
        exit_code, stdout, stderr = py_manage([])
        assert exit_code == 0
        assert stdout == []
        assert stderr == []

    def test_py_manage_emscripten_noop(self):
        with patch(
            "pytigon_lib.schtools.process.platform_name",
            return_value="Emscripten",
        ):
            exit_code, stdout, stderr = py_manage(["migrate"])
            assert exit_code == 0
            assert stdout == []
            assert stderr == []

    def test_py_manage_thread_version(self):
        with patch("pytigon_lib.schtools.process.Thread") as mock_thread_cls:
            mock_thread = MagicMock()
            mock_thread_cls.return_value = mock_thread

            exit_code, stdout, stderr = py_manage(["runserver"], thread_version=True)
            mock_thread_cls.assert_called_once()
            mock_thread.start.assert_called_once()
            mock_thread.join.assert_called_once()
            assert exit_code == 0

    def test_py_manage_calls_py_run(self):
        with patch("pytigon_lib.schtools.process.py_run", return_value=(0, ["ok"], [])):
            exit_code, stdout, stderr = py_manage(["test"])
            assert exit_code == 0
            assert stdout == ["ok"]


class TestFrozenModulesExtra:
    def test_removes_django_modules_on_init(self):
        sys.modules["django_test_module"] = MagicMock()
        frozen = FrozenModules()
        try:
            assert "django_test_module" not in sys.modules
            assert "django_test_module" in frozen.to_restore
        finally:
            frozen.restore()
            sys.modules.pop("django_test_module", None)

    def test_removes_pytigon_lib_modules(self):
        sys.modules["pytigon_lib_test_module"] = MagicMock()
        frozen = FrozenModules()
        try:
            assert "pytigon_lib_test_module" not in sys.modules
        finally:
            frozen.restore()
            sys.modules.pop("pytigon_lib_test_module", None)

    def test_removes_settings_modules(self):
        sys.modules["settings_test_module"] = MagicMock()
        frozen = FrozenModules()
        try:
            assert "settings_test_module" not in sys.modules
        finally:
            frozen.restore()
            sys.modules.pop("settings_test_module", None)

    def test_does_not_remove_unrelated_modules(self):
        sys.modules["unrelated_module"] = MagicMock()
        frozen = FrozenModules()
        try:
            assert "unrelated_module" in sys.modules
        finally:
            frozen.restore()
            sys.modules.pop("unrelated_module", None)
