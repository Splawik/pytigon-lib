"""Tests for :mod:`pytigon_lib.schtools.install_init`."""

import configparser
import os
import sys
import tempfile
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schtools.install_init import (
    _acquire_lock,
    _mkdir,
    _release_lock,
    build_all,
    pip_install,
    upgrade_test,
)


class TestMkdir:
    def test_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            sub = os.path.join(tmp, "subdir")
            assert not os.path.exists(sub)
            _mkdir(sub)
            assert os.path.isdir(sub)

    def test_creates_with_ext(self):
        with tempfile.TemporaryDirectory() as tmp:
            sub = os.path.join(tmp, "parent", "child")
            _mkdir(tmp, "parent")
            _mkdir(os.path.join(tmp, "parent"), "child")
            assert os.path.isdir(sub)

    def test_no_error_when_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            _mkdir(tmp)
            _mkdir(tmp)

    def test_nested_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            deep = os.path.join(tmp, "a", "b", "c")
            _mkdir(deep)
            assert os.path.isdir(deep)

    def test_cannot_create_permission_denied(self, monkeypatch):
        def failing_makedirs(path, exist_ok=False):
            raise OSError("Permission denied")

        monkeypatch.setattr(os, "makedirs", failing_makedirs)
        with tempfile.TemporaryDirectory() as tmp:
            sub = os.path.join(tmp, "sub")
            _mkdir(sub)
            assert not os.path.exists(sub)


class TestUpgradeTest:
    def _make_zip(self, dest, gen_time, filename="install.ini"):
        ini = configparser.ConfigParser()
        ini["DEFAULT"] = {"GEN_TIME": gen_time}
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            ini_path = os.path.join(tmp, filename)
            with open(ini_path, "w") as f:
                ini.write(f)
            with zipfile.ZipFile(dest, "w") as zf:
                zf.write(ini_path, filename)
            zf.close()

    def _make_ini(self, dest_dir, gen_time):
        ini = configparser.ConfigParser()
        ini["DEFAULT"] = {"GEN_TIME": gen_time}
        ini_path = os.path.join(dest_dir, "install.ini")
        with open(ini_path, "w") as f:
            ini.write(f)

    def test_no_zip_returns_false(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            zpath = os.path.join(tmp, "missing.zip")
            assert upgrade_test(zpath, tmp) is False

    def test_newer_zip_returns_true(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            zpath = os.path.join(tmp, "test.zip")
            self._make_zip(zpath, "20250101")
            self._make_ini(tmp, "20240101")
            assert upgrade_test(zpath, tmp) is True

    def test_older_zip_returns_false(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            zpath = os.path.join(tmp, "test.zip")
            self._make_zip(zpath, "20240101")
            self._make_ini(tmp, "20250101")
            assert upgrade_test(zpath, tmp) is False

    def test_equal_times_returns_false(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            zpath = os.path.join(tmp, "test.zip")
            self._make_zip(zpath, "20250101")
            self._make_ini(tmp, "20250101")
            assert upgrade_test(zpath, tmp) is False

    def test_no_existing_ini_returns_false(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            zpath = os.path.join(tmp, "test.zip")
            self._make_zip(zpath, "20250101")
            assert upgrade_test(zpath, tmp) is False


class TestPipInstall:
    def test_confirm_false_returns_false_always(self):
        with patch("pytigon_lib.schtools.install_init.py_run") as mock_py_run:
            mock_py_run.return_value = (0, ["Successfully installed xyz"], [])
            assert pip_install("somepkg", "/tmp/lib", confirm=False) is False

    def test_confirm_true_on_success(self):
        with patch("pytigon_lib.schtools.install_init.py_run") as mock_py_run:
            mock_py_run.return_value = (0, ["Successfully installed xyz"], [])
            assert pip_install("somepkg", "/tmp/lib", confirm=True) is True

    def test_confirm_true_on_failure(self):
        with patch("pytigon_lib.schtools.install_init.py_run") as mock_py_run:
            mock_py_run.return_value = (0, ["Collecting somepkg"], [])
            assert pip_install("somepkg", "/tmp/lib", confirm=True) is False

    def test_success_anywhere_in_output(self):
        with patch("pytigon_lib.schtools.install_init.py_run") as mock_py_run:
            mock_py_run.return_value = (
                0,
                ["line1", "Successfully installed xyz", "line3"],
                [],
            )
            assert pip_install("somepkg", "/tmp/lib", confirm=True) is True

    def test_upgrade_flag_passed(self):
        with patch("pytigon_lib.schtools.install_init.py_run") as mock_py_run:
            mock_py_run.return_value = (0, ["Successfully installed xyz"], [])
            pip_install("somepkg", "/tmp/lib", confirm=False, upgrade=True)
            args = mock_py_run.call_args[0][0]
            assert "--upgrade" in args

    def test_no_upgrade_flag_by_default(self):
        with patch("pytigon_lib.schtools.install_init.py_run") as mock_py_run:
            mock_py_run.return_value = (0, ["Successfully installed xyz"], [])
            pip_install("somepkg", "/tmp/lib", confirm=False)
            args = mock_py_run.call_args[0][0]
            assert "--upgrade" not in args

    def test_target_flag_passed(self):
        with patch("pytigon_lib.schtools.install_init.py_run") as mock_py_run:
            mock_py_run.return_value = (0, ["Successfully installed xyz"], [])
            pip_install("somepkg", "/custom/lib", confirm=False)
            args = mock_py_run.call_args[0][0]
            assert "--target=/custom/lib" in args

    def test_multiple_packages(self):
        with patch("pytigon_lib.schtools.install_init.py_run") as mock_py_run:
            mock_py_run.return_value = (0, ["Successfully installed a b c"], [])
            pip_install("a b c", "/tmp/lib", confirm=False)
            args = mock_py_run.call_args[0][0]
            assert "a" in args
            assert "b" in args
            assert "c" in args

    def test_empty_packages(self):
        with patch("pytigon_lib.schtools.install_init.py_run") as mock_py_run:
            mock_py_run.return_value = (0, [], [])
            pip_install("   ", "/tmp/lib", confirm=False)
            args = mock_py_run.call_args[0][0]
            assert "--disable-pip-version-check" in args
            assert "install" in args


class TestBuildAll:
    def test_no_build_files_returns_true(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            assert build_all(tmp) is True

    def test_successful_build(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            script = os.path.join(tmp, "example_build.py")
            with open(script, "w") as f:
                f.write("def build(path=None):\n    return True")
            assert build_all(tmp) is True

    def test_failed_build_returns_false(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            script = os.path.join(tmp, "example_build.py")
            with open(script, "w") as f:
                f.write("def build(path=None):\n    return False")
            assert build_all(tmp) is False

    def test_passes_path_argument(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            script = os.path.join(tmp, "example_build.py")
            expected = os.path.join(tmp, "example.nim")
            s = f"def build(path=None):\n    if path != {expected!r}:\n        return False\n    return True"
            with open(script, "w") as f:
                f.write(s)
            assert build_all(tmp) is True

    def test_ignores_non_build_files(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            script = os.path.join(tmp, "other_script.py")
            with open(script, "w") as f:
                f.write("def build(path=None):\n    return True")
            assert build_all(tmp) is True


class TestLockAcquireRelease:
    def test_acquire_no_multiprocessing(self, monkeypatch):
        monkeypatch.setitem(sys.modules, "multiprocessing", None)
        lock = _acquire_lock()
        assert lock is None

    def test_acquire_oserror(self):
        with patch("multiprocessing.Lock") as mock_lock:
            mock_lock.side_effect = OSError
            lock = _acquire_lock()
            assert lock is None

    def test_acquire_success(self):
        with patch("multiprocessing.Lock") as mock_lock:
            mock = MagicMock()
            mock_lock.return_value = mock
            lock = _acquire_lock()
            assert lock is mock
            mock.acquire.assert_called_once()

    def test_release_none_does_nothing(self):
        lock = None
        _release_lock(lock)

    def test_release_valid_lock(self):
        mock_lock = MagicMock()
        _release_lock(mock_lock)
        mock_lock.release.assert_called_once()

    def test_release_lock_exception_ignored(self):
        mock_lock = MagicMock()
        mock_lock.release.side_effect = RuntimeError("already released")
        _release_lock(mock_lock)
        mock_lock.release.assert_called_once()
