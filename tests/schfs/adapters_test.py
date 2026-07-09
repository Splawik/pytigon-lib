"""Tests for :mod:`pytigon_lib.schfs.adapters`."""

import datetime
import io
import os
import tempfile

import pytest

from pytigon_lib.schfs.adapters import (
    _AutoCreateLocalFs,
    _FsspecInfo,
    _FsspecInfoExt,
    _fsspec_abspath,
    _fsspec_dirname,
    _fsspec_join,
    FsspecMountFS,
    FsspecMultiFS,
)


class TestFsspecInfo:
    def test_size(self):
        info = _FsspecInfo({"size": 1024})
        assert info.size == 1024

    def test_size_default(self):
        info = _FsspecInfo({})
        assert info.size == 0

    def test_modified_datetime(self):
        dt = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)
        info = _FsspecInfo({"mtime": dt})
        assert info.modified == dt

    def test_modified_timestamp(self):
        info = _FsspecInfo({"mtime": 1704067200})
        assert info.modified is not None

    def test_modified_none(self):
        info = _FsspecInfo({})
        assert info.modified is None

    def test_created(self):
        dt = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)
        info = _FsspecInfo({"created": dt})
        assert info.created == dt

    def test_accessed(self):
        dt = datetime.datetime(2024, 1, 1, tzinfo=datetime.UTC)
        info = _FsspecInfo({"atime": dt})
        assert info.accessed == dt

    def test_isdir_true(self):
        info = _FsspecInfo({"type": "directory"})
        assert info.isdir is True

    def test_isdir_false(self):
        info = _FsspecInfo({"type": "file"})
        assert info.isdir is False

    def test_name(self):
        info = _FsspecInfo({"name": "/path/to/file.txt"})
        assert info.name == "file.txt"

    def test_name_empty(self):
        info = _FsspecInfo({})
        assert info.name == ""

    def test_raw(self):
        data = {"size": 42, "type": "file"}
        info = _FsspecInfo(data)
        assert info.raw == {"size": 42, "type": "file"}
        info.raw["new"] = 1
        assert "new" not in info._info


class TestFsspecInfoExt:
    def test_type(self):
        info = _FsspecInfoExt({"type": "file"})
        assert info.type == "file"

    def test_type_default(self):
        info = _FsspecInfoExt({})
        assert info.type == ""


class TestFsspecAbsPath:
    def test_simple(self):
        assert _fsspec_abspath("/a/b/c") == "/a/b/c"

    def test_double_dots(self):
        assert _fsspec_abspath("/a/b/../c") == "/a/c"

    def test_multiple_dots(self):
        assert _fsspec_abspath("/a/b/../../d") == "/d"

    def test_single_dots(self):
        assert _fsspec_abspath("/a/./b/./c") == "/a/b/c"

    def test_empty(self):
        assert _fsspec_abspath("") == ""

    def test_root(self):
        assert _fsspec_abspath("/") == "/"

    def test_trailing_slash(self):
        result = _fsspec_abspath("/a/b/")
        assert result.endswith("b") or result == "/a/b"


class TestFsspecDirname:
    def test_simple(self):
        assert _fsspec_dirname("/a/b/c") == "/a/b"

    def test_root(self):
        result = _fsspec_dirname("/a")
        assert result == "" or result == "/"

    def test_no_slash(self):
        assert _fsspec_dirname("file") == ""

    def test_empty(self):
        result = _fsspec_dirname("")
        assert result in ("", "/")


class TestFsspecJoin:
    def test_two_parts(self):
        assert _fsspec_join("a", "b") == "/a/b"

    def test_three_parts(self):
        assert _fsspec_join("a", "b", "c") == "/a/b/c"

    def test_with_slash_prefix(self):
        assert _fsspec_join("/a", "/b") == "/a/b"

    def test_empty_parts(self):
        assert _fsspec_join("a", "", "c") == "/a/c"

    def test_no_args(self):
        assert _fsspec_join() == "/"


class TestAutoCreateLocalFs:
    def test_init(self):
        fs = _AutoCreateLocalFs("/tmp")
        assert fs._root == os.path.abspath("/tmp")


class TestFsspecMountFS:
    def test_init_empty(self):
        fs = FsspecMountFS()
        assert fs._mounts == {}
        assert fs._order == []

    def test_mount_and_resolve(self):
        class FakeFs:
            def open(self, path, mode="rb", **kw):
                if mode == "rb" and not path.startswith("/"):
                    raise FileNotFoundError(path)
                return io.BytesIO(b"test")

                def isfile(self, path):
                    return path == "test.txt"

                def isdir(self, path):
                    return path == "" or path == "dir"

                def exists(self, path):
                    return path in ("test.txt", "dir", "")

                def scandir(self, path):
                    return []

                def listdir(self, path):
                    return []

                def getinfo(self, path, namespaces=None):
                    return _FsspecInfo({"name": path, "size": 0})

                def info(self, path):
                    return {"name": path, "size": 0, "type": "file"}

                def size(self, path):
                    return 0

        fs = FsspecMountFS()
        fake = FakeFs()
        fs.mount("test", fake)
        assert "test" in fs._mounts

    def test_mount_strips_slash(self):
        fs = FsspecMountFS()
        fs.mount("/pytigon/", "dummy")
        assert "pytigon" in fs._mounts

    def test_mounts_property(self):
        fs = FsspecMountFS()
        fs.mount("app", "dummy1")
        fs.mount("static", "dummy2")
        mounts = fs.mounts
        assert len(mounts) == 2

    def test_add_fs_existing_creates_multi(self):
        fs = FsspecMountFS()
        fs.mount("app", "fs1")
        fs.add_fs("app", "fs2")
        assert isinstance(fs._mounts["app"], FsspecMultiFS)

    def test_add_fs_new_creates_entry(self):
        fs = FsspecMountFS()
        fs.add_fs("newapp", "fs1")
        assert "newapp" in fs._mounts

    def test_resolve_empty_path(self):
        fs = FsspecMountFS()
        fs.mount("default", "fs1")
        result = fs._resolve("/")
        assert result[0] is not None or result[1] == "/"

    def test_resolve_unknown_prefix_falls_back(self):
        fs = FsspecMountFS()
        fs.mount("known", "fs1")
        result = fs._resolve("/unknown/file.txt")
        assert result[0] == "fs1"

    def test_resolve_none(self):
        fs = FsspecMountFS()
        result = fs._resolve("/anything")
        assert result[0] is None

    def test_repr(self):
        fs = FsspecMountFS()
        fs.mount("test", "dummy")
        assert "test" in repr(fs)


class TestFsspecMultiFS:
    def test_init_empty(self):
        fs = FsspecMultiFS()
        assert fs._fs_list == []

    def test_add_fs(self):
        fs = FsspecMultiFS()
        fs.add_fs("a", "fs_a")
        assert len(fs._fs_list) == 1
        assert fs._fs_list[0] == ("a", "fs_a")

    def test_add_multiple_fs(self):
        fs = FsspecMultiFS()
        fs.add_fs("a", "fs_a")
        fs.add_fs("b", "fs_b")
        assert len(fs._fs_list) == 2

    def test_open_file_not_found(self):
        fs = FsspecMultiFS()
        with pytest.raises(FileNotFoundError):
            fs.open("nonexistent")

    def test_repr(self):
        fs = FsspecMultiFS()
        fs.add_fs("test_fs", None)
        assert "test_fs" in repr(fs)
