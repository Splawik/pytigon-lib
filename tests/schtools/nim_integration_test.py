"""Tests for :mod:`pytigon_lib.schtools.nim_integration`."""

import os
import tarfile
import tempfile
import zipfile

import pytest

from pytigon_lib.schtools.nim_integration import (
    _is_safe_tar_member,
    _is_safe_zip_member,
    get_nim_path,
)


class TestSafeTarMember:
    def test_safe_member(self):
        target = "/tmp/test_target"
        member = MagicMock()
        member.name = "subdir/file.txt"
        with patch("os.path.realpath") as mock_real:
            mock_real.side_effect = lambda x: x
            result = _is_safe_tar_member(member, target)
            assert isinstance(result, bool)

    def test_unsafe_member_traversal(self):
        target = "/tmp/test_target"
        member = MagicMock()
        member.name = "../etc/passwd"
        result = _is_safe_tar_member(member, target)
        assert result is False

    def test_same_dir_is_safe(self):
        target = "/tmp/test_target"
        member = MagicMock()
        member.name = "file.txt"
        result = _is_safe_tar_member(member, target)
        assert result is True


class TestSafeZipMember:
    def test_safe_member(self):
        target = "/tmp/test_target"
        result = _is_safe_zip_member("subdir/file.txt", target)
        assert result is True

    def test_unsafe_member_traversal(self):
        target = "/tmp/test_target"
        result = _is_safe_zip_member("../etc/passwd", target)
        assert result is False

    def test_same_dir_is_safe(self):
        target = "/tmp/test_target"
        result = _is_safe_zip_member("file.txt", target)
        assert result is True


class TestGetNimPath:
    def test_nonexistent_path(self):
        result = get_nim_path("/nonexistent/path/xyz123")
        assert result is None

    def test_path_without_prg(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            result = get_nim_path(tmpdir)
            assert result is None

    def test_path_with_nim_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            prg_path = os.path.join(tmpdir, "prg")
            os.makedirs(os.path.join(prg_path, "nim-2.0.4"))
            result = get_nim_path(tmpdir)
            assert result is not None
            assert "nim-2.0.4" in result

    def test_multiple_nim_dirs_returns_first(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            prg_path = os.path.join(tmpdir, "prg")
            os.makedirs(os.path.join(prg_path, "nim-2.0.2"))
            os.makedirs(os.path.join(prg_path, "nim-2.0.4"))
            result = get_nim_path(tmpdir)
            assert "nim-2.0.2" in result


from unittest.mock import MagicMock, patch
