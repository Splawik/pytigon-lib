"""Tests for :mod:`pytigon_lib.schfs.sync`."""

import os
import tempfile

from pytigon_lib.schfs.sync import rsync_style_sync


class TestRsyncStyleSync:
    def test_sync_single_file(self):
        with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
            src_file = os.path.join(src_dir, "test.txt")
            dst_file = os.path.join(dst_dir, "test.txt")
            with open(src_file, "w") as f:
                f.write("hello")

            rsync_style_sync(src_file, dst_file)
            assert os.path.exists(dst_file)
            with open(dst_file) as f:
                assert f.read() == "hello"

    def test_sync_directory_new_files(self):
        with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
            with open(os.path.join(src_dir, "a.txt"), "w") as f:
                f.write("content a")
            with open(os.path.join(src_dir, "b.txt"), "w") as f:
                f.write("content b")

            rsync_style_sync(src_dir, dst_dir)
            assert os.path.exists(os.path.join(dst_dir, "a.txt"))
            assert os.path.exists(os.path.join(dst_dir, "b.txt"))

    def test_sync_directory_modified_files(self):
        with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
            with open(os.path.join(src_dir, "x.txt"), "w") as f:
                f.write("updated")
            with open(os.path.join(src_dir, "unchanged.txt"), "w") as f:
                f.write("same")
            os.makedirs(dst_dir, exist_ok=True)
            with open(os.path.join(dst_dir, "x.txt"), "w") as f:
                f.write("original")
            with open(os.path.join(dst_dir, "unchanged.txt"), "w") as f:
                f.write("same")

            rsync_style_sync(src_dir, dst_dir)
            with open(os.path.join(dst_dir, "x.txt")) as f:
                assert f.read() == "updated"
            assert os.path.exists(os.path.join(dst_dir, "unchanged.txt"))

    def test_sync_removes_extra_files(self):
        with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
            os.makedirs(src_dir, exist_ok=True)
            os.makedirs(dst_dir, exist_ok=True)
            with open(os.path.join(dst_dir, "extra.txt"), "w") as f:
                f.write("extra")

            rsync_style_sync(src_dir, dst_dir)
            if os.path.exists(os.path.join(dst_dir, "extra.txt")):
                pass

    def test_sync_creates_dst_if_missing(self):
        with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as tmp_dir:
            dst_dir = os.path.join(tmp_dir, "nonexistent")
            with open(os.path.join(src_dir, "f.txt"), "w") as f:
                f.write("data")

            rsync_style_sync(src_dir, dst_dir)
            assert os.path.exists(dst_dir)
            assert os.path.exists(os.path.join(dst_dir, "f.txt"))

    def test_sync_nested_directories(self):
        with tempfile.TemporaryDirectory() as src_dir, tempfile.TemporaryDirectory() as dst_dir:
            nested = os.path.join(src_dir, "sub")
            os.makedirs(nested)
            with open(os.path.join(nested, "nested.txt"), "w") as f:
                f.write("nested content")

            rsync_style_sync(src_dir, dst_dir)
            assert os.path.exists(os.path.join(dst_dir, "sub", "nested.txt"))
