"""Tests for :mod:`pytigon_lib.schfs.download` utilities."""

import io
import os
import tarfile
import tempfile
import zipfile

import pytest

from pytigon_lib.schfs.download import (
    _is_safe_tar_member,
    _is_safe_url,
    _is_safe_zip_member,
    _safe_tar_extractall,
    _safe_zip_extractall,
)


class TestIsSafeUrl:
    def test_https_public_url(self):
        assert _is_safe_url("https://example.com/file.zip") is True

    def test_http_public_url(self):
        assert _is_safe_url("http://cdn.example.org/data.tar.gz") is True

    def test_ftp_unsafe(self):
        assert _is_safe_url("ftp://server/file") is False

    def test_file_unsafe(self):
        assert _is_safe_url("file:///etc/passwd") is False

    def test_localhost_unsafe(self):
        assert _is_safe_url("http://localhost:8080/test") is False

    def test_127_0_0_1_unsafe(self):
        assert _is_safe_url("http://127.0.0.1/admin") is False

    def test_0_0_0_0_unsafe(self):
        assert _is_safe_url("http://0.0.0.0/test") is False

    def test_ipv6_localhost_unsafe(self):
        assert _is_safe_url("http://[::1]/test") is False

    def test_ipv6_full_unsafe(self):
        assert _is_safe_url("http://[0:0:0:0:0:0:0:1]/test") is False

    def test_private_192_168_unsafe(self):
        assert _is_safe_url("http://192.168.1.1/test") is False

    def test_private_10_unsafe(self):
        assert _is_safe_url("http://10.0.0.1/test") is False

    def test_private_172_16_unsafe(self):
        assert _is_safe_url("http://172.16.0.1/test") is False

    def test_private_172_31_unsafe(self):
        assert _is_safe_url("http://172.31.255.255/test") is False

    def test_private_169_254_unsafe(self):
        assert _is_safe_url("http://169.254.0.1/test") is False

    def test_broadcast_unsafe(self):
        assert _is_safe_url("http://255.255.255.255/test") is False

    def test_no_hostname(self):
        assert _is_safe_url("http:///path") is False

    def test_ws_scheme_unsafe(self):
        assert _is_safe_url("ws://example.com/socket") is False


class TestSafeTarMember:
    def test_safe_member(self):
        member = tarfile.TarInfo("subdir/file.txt")
        assert _is_safe_tar_member(member, "/tmp/test") is True

    def test_traversal_unsafe(self):
        member = tarfile.TarInfo("../etc/passwd")
        assert _is_safe_tar_member(member, "/tmp/test") is False


class TestSafeZipMember:
    def test_safe_member(self):
        assert _is_safe_zip_member("subdir/file.txt", "/tmp/test") is True

    def test_traversal_unsafe(self):
        assert _is_safe_zip_member("../etc/passwd", "/tmp/test") is False


class TestSafeExtract:
    def test_zip_extractall_safe(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "test.zip")
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("hello.txt", "hello world")
                zf.writestr("nested/deep.txt", "deep")

            target = os.path.join(tmpdir, "extracted")
            with zipfile.ZipFile(zip_path, "r") as zf:
                _safe_zip_extractall(zf, target)

            assert os.path.exists(os.path.join(target, "hello.txt"))
            assert os.path.exists(os.path.join(target, "nested", "deep.txt"))

    def test_zip_skips_traversal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            zip_path = os.path.join(tmpdir, "test.zip")
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("safe.txt", "safe")

            target = os.path.join(tmpdir, "extracted")
            with zipfile.ZipFile(zip_path, "r") as zf:
                _safe_zip_extractall(zf, target)
            assert os.path.exists(os.path.join(target, "safe.txt"))

    def test_tar_extractall_safe(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tar_path = os.path.join(tmpdir, "test.tar")
            with tarfile.open(tar_path, "w") as tf:
                data = b"hello"
                info = tarfile.TarInfo("file.txt")
                info.size = len(data)
                tf.addfile(info, io.BytesIO(data))

            target = os.path.join(tmpdir, "extracted")
            with tarfile.open(tar_path, "r") as tf:
                _safe_tar_extractall(tf, target)

            assert os.path.exists(os.path.join(target, "file.txt"))
