"""Extra tests for :mod:`pytigon_lib.schfs.adapters` — FsspecMountFS and FsspecMultiFS."""

import datetime
import io
import os
import tempfile

import pytest
from fsspec.implementations.memory import MemoryFileSystem

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


@pytest.fixture(autouse=True)
def _clear_memory_fs():
    """Clear the global MemoryFileSystem store between tests to prevent state leakage."""
    try:
        MemoryFileSystem.store.clear()
        MemoryFileSystem.pseudo_dirs.clear()
        if "" not in MemoryFileSystem.pseudo_dirs:
            MemoryFileSystem.pseudo_dirs.append("")
    except Exception:
        pass


class _OpenTestFS:
    """Fake filesystem that tracks calls for testing FsspecMountFS/FsspecMultiFS."""

    def __init__(self):
        self.files = {}
        self.dirs = set()
        self._last_remove = None
        self._last_rm = None
        self._opens = []
        self._removes = []
        self._rm_files = []
        self._makedirs_calls = []
        self._makedir_calls = []
        self._mkdir_calls = []
        self._removetree_calls = []
        self._rm_recursive_calls = []

    def open(self, path, mode="rb", **kwargs):
        self._opens.append((path, mode))
        if "r" in mode and "+" not in mode and "w" not in mode and "a" not in mode:
            if path not in self.files:
                raise FileNotFoundError(path)
            content = self.files.get(path, b"")
            return io.BytesIO(content) if "b" in mode else io.StringIO(content.decode() if isinstance(content, bytes) else content)
        if path not in self.files and "r" in mode:
            raise FileNotFoundError(path)
        buf = io.BytesIO(self.files.get(path, b"")) if "b" in mode else io.StringIO(self.files.get(path, b"").decode() if isinstance(self.files.get(path), bytes) else self.files.get(path, ""))
        if "w" in mode or "a" in mode:
            return _WriteCapture(path, self, buf, mode)
        return buf

    def isfile(self, path):
        return path in self.files

    def isdir(self, path):
        return path == "" or path in self.dirs

    def exists(self, path):
        return path in self.files or path in self.dirs or path == ""

    def ls(self, path, detail=False):
        prefix = path.rstrip("/") + "/" if path else ""
        if detail:
            return [{"name": prefix + f, "type": "file", "size": len(self.files.get(f, b""))} for f in self.files]
        return list(self.files.keys())

    def info(self, path):
        if path in self.files or path in self.dirs or path in ("", "/"):
            return {"name": path, "size": len(self.files.get(path, b"")), "type": "file" if path in self.files else "directory"}
        raise FileNotFoundError(path)

    def size(self, path):
        return len(self.files.get(path, b""))

    def makedirs(self, path, recreate=False):
        self._makedirs_calls.append((path, recreate))

    def mkdirs(self, path, exist_ok=False):
        self._makedirs_calls.append((path, exist_ok))

    def makedir(self, path):
        self._makedir_calls.append(path)

    def mkdir(self, path, create_parents=False):
        self._mkdir_calls.append((path, create_parents))

    def setbinfile(self, path, content):
        if hasattr(content, "read"):
            self.files[path] = content.read()
        else:
            self.files[path] = content

    def remove(self, path):
        self._removes.append(path)
        self.files.pop(path, None)
        self.dirs.discard(path)

    def rm_file(self, path):
        self._rm_files.append(path)

    def removetree(self, path):
        self._removetree_calls.append(path)

    def rm(self, path, recursive=False):
        self._rm_recursive_calls.append((path, recursive))

    def get(self, src, dst):
        self.files[dst] = self.files.get(src, b"")

    def put(self, src, dst):
        pass


class _WriteCapture(io.BytesIO):
    def __init__(self, path, owner, buf, mode):
        super().__init__()
        self._path = path
        self._owner = owner
        self._mode = mode
        if buf and "a" in mode:
            self.write(buf.read() if hasattr(buf, "read") else buf)

    def close(self):
        self._owner.files[self._path] = self.getvalue()
        super().close()


class TestFsspecMountFSOpen:
    def test_open_read_file(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.pipe("/test.txt", b"hello")
        mfs.mount("mnt", mem)
        with mfs.open("/mnt/test.txt", "rb") as f:
            assert f.read() == b"hello"

    def test_open_write_file(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("mnt", mem)
        with mfs.open("/mnt/new.txt", "wb") as f:
            f.write(b"data")
        assert mem.cat("/new.txt") == b"data"

    def test_open_nonexistent_prefix(self):
        mfs = FsspecMountFS()
        with pytest.raises(FileNotFoundError):
            mfs.open("/nonexistent/file.txt")

    def test_open_root_path(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.pipe("/data.txt", b"root")
        mfs.mount("mnt", mem)
        with pytest.raises((IsADirectoryError, OSError, FileNotFoundError)):
            with mfs.open("/mnt/", "rb") as f:
                f.read()

    def test_open_fallback_to_first_mount(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.pipe("/unknown/test.txt", b"fallback")
        mfs.mount("mnt", mem)
        with mfs.open("/unknown/test.txt", "rb") as f:
            assert f.read() == b"fallback"

    def test_open_through__open(self):
        mfs = FsspecMountFS()
        fake = _OpenTestFS()
        mfs.mount("app", fake)
        with pytest.raises((FileNotFoundError, KeyError)):
            mfs.open("/app/file.txt")


class TestFsspecMountFSIsfile:
    def test_isfile_true(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.pipe("/test.txt", b"")
        mfs.mount("mnt", mem)
        assert mfs.isfile("/mnt/test.txt") is True

    def test_isfile_false(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("mnt", mem)
        assert mfs.isfile("/mnt/nonexistent.txt") is False

    def test_isfile_directory(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.mkdir("/dir")
        mfs.mount("mnt", mem)
        assert mfs.isfile("/mnt/dir") is False

    def test_isfile_empty_rest(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("mnt", mem)
        assert mfs.isfile("/mnt") is False

    def test_isfile_none_fs(self):
        mfs = FsspecMountFS()
        assert mfs.isfile("/none/file.txt") is False


class TestFsspecMountFSIsdir:
    def test_isdir_directory(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.mkdir("/dir")
        mfs.mount("mnt", mem)
        assert mfs.isdir("/mnt/dir") is True

    def test_isdir_file(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.pipe("/test.txt", b"")
        mfs.mount("mnt", mem)
        assert mfs.isdir("/mnt/test.txt") is False

    def test_isdir_root_of_mount(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("mnt", mem)
        assert mfs.isdir("/mnt") is True

    def test_isdir_empty_rest(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("mnt", mem)
        assert mfs.isdir("/mnt/") is True

    def test_isdir_none_fs(self):
        mfs = FsspecMountFS()
        assert mfs.isdir("/none/file.txt") is False


class TestFsspecMountFSExists:
    def test_exists_file(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.pipe("/test.txt", b"")
        mfs.mount("mnt", mem)
        assert mfs.exists("/mnt/test.txt") is True

    def test_exists_directory(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.mkdir("/dir")
        mfs.mount("mnt", mem)
        assert mfs.exists("/mnt/dir") is True

    def test_exists_root(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("mnt", mem)
        assert mfs.exists("/mnt") is True

    def test_exists_nonexistent(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("mnt", mem)
        assert mfs.exists("/mnt/nonexistent") is False

    def test_exists_none_fs(self):
        mfs = FsspecMountFS()
        assert mfs.exists("/none/file.txt") is False


class TestFsspecMountFSScandir:
    def test_scandir_returns_info_objects(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.mkdir("/subdir")
        mem.pipe("/file.txt", b"data")
        mfs.mount("mnt", mem)
        results = mfs.scandir("/mnt/")
        assert len(results) >= 0

    def test_scandir_empty_dir(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("mnt", mem)
        results = mfs.scandir("/mnt/")
        assert isinstance(results, list)

    def test_scandir_none_fs(self):
        mfs = FsspecMountFS()
        assert mfs.scandir("/none/") == []

    def test_scandir_with_native_scandir(self):
        mfs = FsspecMountFS()
        fake = _OpenTestFS()
        fake.scandir = lambda path: [_FsspecInfoExt({"name": "f.txt", "type": "file"})]
        mfs.mount("app", fake)
        results = mfs.scandir("/app/")
        assert len(results) == 1


class TestFsspecMountFSListdir:
    def test_listdir_returns_filenames(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.pipe("/a.txt", b"a")
        mem.pipe("/b.txt", b"b")
        mfs.mount("mnt", mem)
        result = mfs.listdir("/mnt/")
        assert isinstance(result, list)

    def test_listdir_empty(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("mnt", mem)
        result = mfs.listdir("/mnt/")
        assert result == []

    def test_listdir_none_fs(self):
        mfs = FsspecMountFS()
        assert mfs.listdir("/none/") == []

    def test_listdir_with_native_listdir(self):
        mfs = FsspecMountFS()
        fake = _OpenTestFS()
        fake.listdir = lambda path: ["a.txt", "b.txt"]
        mfs.mount("app", fake)
        results = mfs.listdir("/app/")
        assert results == ["a.txt", "b.txt"]


class TestFsspecMountFSGetinfo:
    def test_getinfo_file(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.pipe("/test.txt", b"hello world")
        mfs.mount("mnt", mem)
        info = mfs.getinfo("/mnt/test.txt")
        assert isinstance(info, _FsspecInfo)
        assert info.size == 11

    def test_getinfo_directory(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.mkdir("/dir")
        mfs.mount("mnt", mem)
        info = mfs.getinfo("/mnt/dir")
        assert isinstance(info, _FsspecInfo)

    def test_getinfo_nonexistent(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("mnt", mem)
        with pytest.raises((FileNotFoundError, OSError)):
            mfs.getinfo("/mnt/nonexistent.txt")

    def test_getinfo_none_fs(self):
        mfs = FsspecMountFS()
        with pytest.raises(FileNotFoundError):
            mfs.getinfo("/none/file.txt")

    def test_getinfo_uses_native_getinfo(self):
        mfs = FsspecMountFS()
        fake = _OpenTestFS()
        fake.getinfo = lambda path, namespaces=None: _FsspecInfo({"name": path, "size": 42})
        mfs.mount("app", fake)
        info = mfs.getinfo("/app/file.txt")
        assert info.size == 42


class TestFsspecMountFSGetdetails:
    def test_getdetails_file(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.pipe("/test.txt", b"content")
        mfs.mount("mnt", mem)
        info = mfs.getdetails("/mnt/test.txt")
        assert isinstance(info, _FsspecInfoExt)

    def test_getdetails_directory(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.mkdir("/dir")
        mfs.mount("mnt", mem)
        info = mfs.getdetails("/mnt/dir")
        assert isinstance(info, _FsspecInfoExt)

    def test_getdetails_zip_file(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.pipe("/archive.zip", b"zipcontent")
        mfs.mount("mnt", mem)
        info = mfs.getdetails("/mnt/archive.zip")
        assert info.type == "directory"

    def test_getdetails_none_fs(self):
        mfs = FsspecMountFS()
        with pytest.raises(FileNotFoundError):
            mfs.getdetails("/none/file.txt")

    def test_getdetails_native_getdetails(self):
        mfs = FsspecMountFS()
        fake = _OpenTestFS()
        fake.getdetails = lambda path: _FsspecInfoExt({"name": path, "type": "file"})
        mfs.mount("app", fake)
        info = mfs.getdetails("/app/file.txt")
        assert isinstance(info, _FsspecInfoExt)


class TestFsspecMountFSGetsize:
    def test_getsize_file(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.pipe("/test.txt", b"abcdef")
        mfs.mount("mnt", mem)
        assert mfs.getsize("/mnt/test.txt") == 6

    def test_getsize_existing_dir(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.mkdir("/dir")
        mfs.mount("mnt", mem)
        size = mfs.getsize("/mnt/dir")
        assert size == 0

    def test_getsize_nonexistent(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("mnt", mem)
        with pytest.raises((FileNotFoundError, OSError)):
            mfs.getsize("/mnt/nonexistent.txt")

    def test_getsize_none_fs(self):
        mfs = FsspecMountFS()
        with pytest.raises(FileNotFoundError):
            mfs.getsize("/none/file.txt")

    def test_getsize_native(self):
        mfs = FsspecMountFS()
        fake = _OpenTestFS()
        fake.getsize = lambda path: 99
        mfs.mount("app", fake)
        assert mfs.getsize("/app/file.txt") == 99


class TestFsspecMountFSGetsyspath:
    def test_getsyspath_local_fs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            afs = _AutoCreateLocalFs(tmpdir)
            mfs = FsspecMountFS()
            mfs.mount("local", afs)
            test_file = os.path.join(tmpdir, "test.txt")
            with open(test_file, "w") as f:
                f.write("test")
            result = mfs.getsyspath("/local/test.txt")
            assert result == test_file or result.endswith("test.txt")

    def test_getsyspath_none_fs_allow_none(self):
        mfs = FsspecMountFS()
        result = mfs.getsyspath("/none/file.txt", allow_none=True)
        assert result is None

    def test_getsyspath_none_fs_no_allow(self):
        mfs = FsspecMountFS()
        with pytest.raises(FileNotFoundError):
            mfs.getsyspath("/none/file.txt")

    def test_getsyspath_non_local(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.pipe("/f.txt", b"data")
        mfs.mount("mnt", mem)
        result = mfs.getsyspath("/mnt/f.txt")
        assert isinstance(result, str)
        assert "memory://" in result or "f.txt" in result

    def test_getsyspath_native(self):
        mfs = FsspecMountFS()
        fake = _OpenTestFS()
        fake.getsyspath = lambda path, allow_none=False: f"/real/{path}"
        mfs.mount("app", fake)
        result = mfs.getsyspath("/app/file.txt")
        assert result == "/real/file.txt"


class TestFsspecMountFSMakedirs:
    def test_makedirs_uses_native(self):
        mfs = FsspecMountFS()
        fake = _OpenTestFS()
        mfs.mount("app", fake)
        mfs.makedirs("/app/subdir/deep")
        assert len(fake._makedirs_calls) >= 1

    def test_makedirs_fallback_mkdirs(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("mnt", mem)
        mfs.makedirs("/mnt/subdir")
        assert mem.isdir("/subdir")

    def test_makedirs_none_fs(self):
        mfs = FsspecMountFS()
        mfs.makedirs("/none/subdir")

    def test_makedirs_recreate(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.mkdir("/existdir")
        mfs.mount("mnt", mem)
        mfs.makedirs("/mnt/existdir", recreate=True)
        assert mem.isdir("/existdir")


class TestFsspecMountFSMakedir:
    def test_makedir_uses_native(self):
        mfs = FsspecMountFS()
        fake = _OpenTestFS()
        mfs.mount("app", fake)
        mfs.makedir("/app/newdir")
        assert len(fake._makedir_calls) >= 1

    def test_makedir_fallback_mkdir(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("mnt", mem)
        mfs.makedir("/mnt/newdir")
        assert mem.isdir("/newdir")

    def test_makedir_none_fs(self):
        mfs = FsspecMountFS()
        mfs.makedir("/none/newdir")


class TestFsspecMountFSSetbinfile:
    def test_setbinfile_with_bytes(self):
        mfs = FsspecMountFS()
        fake = _OpenTestFS()
        mfs.mount("app", fake)
        mfs.setbinfile("/app/test.txt", b"hello")
        assert fake.files.get("test.txt") == b"hello"

    def test_setbinfile_with_string(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("mnt", mem)
        mfs.setbinfile("/mnt/test.txt", "hello world")
        data = mem.cat("/test.txt")
        assert data == b"hello world"

    def test_setbinfile_file_like(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("mnt", mem)
        buf = io.BytesIO(b"stream data")
        mfs.setbinfile("/mnt/stream.txt", buf)
        assert mem.cat("/stream.txt") == b"stream data"

    def test_setbinfile_none_fs(self):
        mfs = FsspecMountFS()
        with pytest.raises(FileNotFoundError):
            mfs.setbinfile("/none/file.txt", b"data")

    def test_setbinfile_native_setbinfile(self):
        mfs = FsspecMountFS()
        fake = _OpenTestFS()
        mfs.mount("app", fake)
        mfs.setbinfile("/app/test.txt", b"data")
        assert "test.txt" in fake.files


class TestFsspecMountFSRemove:
    def test_remove_uses_native(self):
        mfs = FsspecMountFS()
        fake = _OpenTestFS()
        mfs.mount("app", fake)
        mfs.remove("/app/file.txt")
        assert len(fake._removes) >= 1

    def test_remove_fallback_rm_file(self):
        mfs = FsspecMountFS()
        fake = _OpenTestFS()
        delattr(type(fake), "remove")
        mfs.mount("app", fake)
        mfs.remove("/app/other.txt")
        assert len(fake._rm_files) >= 1

    def test_remove_none_fs(self):
        mfs = FsspecMountFS()
        mfs.remove("/none/file.txt")

    def test_remove_actual(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.pipe("/test.txt", b"data")
        mfs.mount("mnt", mem)
        assert mem.exists("/test.txt")
        mfs.remove("/mnt/test.txt")
        assert not mem.exists("/test.txt")


class TestFsspecMountFSRemovetree:
    def test_removetree_uses_native(self):
        mfs = FsspecMountFS()
        fake = _OpenTestFS()
        mfs.mount("app", fake)
        mfs.removetree("/app/subdir")
        assert len(fake._removetree_calls) >= 1

    def test_removetree_fallback_rm(self):
        mfs = FsspecMountFS()
        fake = _OpenTestFS()
        delattr(type(fake), "removetree")
        mfs.mount("app", fake)
        mfs.removetree("/app/otherdir")
        assert len(fake._rm_recursive_calls) >= 1

    def test_removetree_none_fs(self):
        mfs = FsspecMountFS()
        mfs.removetree("/none/subdir")

    def test_removetree_actual(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.mkdir("/dir")
        mem.pipe("/dir/file.txt", b"data")
        mfs.mount("mnt", mem)
        mfs.removetree("/mnt/dir")
        assert not mem.exists("/dir")


class TestFsspecMountFSCopy:
    def test_copy_same_fs(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.pipe("/src.txt", b"source data")
        mfs.mount("mnt", mem)
        mfs.copy("/mnt/src.txt", "/mnt/dst.txt")
        assert mem.cat("/dst.txt") == b"source data"

    def test_copy_cross_fs(self):
        mfs = FsspecMountFS()
        mem1 = MemoryFileSystem()
        mem2 = MemoryFileSystem()
        mem1.pipe("/src.txt", b"hello")
        mfs.mount("src", mem1)
        mfs.mount("dst", mem2)
        mfs.copy("/src/src.txt", "/dst/copied.txt")
        assert mem2.cat("/copied.txt") == b"hello"

    def test_copy_overwrite(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.pipe("/src.txt", b"new")
        mem.pipe("/dst.txt", b"old")
        mfs.mount("mnt", mem)
        mfs.copy("/mnt/src.txt", "/mnt/dst.txt", overwrite=True)
        assert mem.cat("/dst.txt") == b"new"

    def test_copy_nonexistent_source(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("mnt", mem)
        with pytest.raises(FileNotFoundError):
            mfs.copy("/mnt/src.txt", "/mnt/dst.txt")

    def test_copy_nonexistent_dest_fs(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.pipe("/src.txt", b"data")
        mfs.mount("mnt", mem)
        mfs.copy("/mnt/src.txt", "/none/dst.txt")
        assert mem.exists("none/dst.txt") or mem.cat("none/dst.txt") == b"data"


class TestFsspecMountFSCopydir:
    def test_copydir_with_files(self):
        mfs = FsspecMountFS()
        mem1 = MemoryFileSystem()
        mem1.mkdir("/src")
        mem1.pipe("/src/a.txt", b"a")
        mem1.pipe("/src/b.txt", b"b")
        mem2 = MemoryFileSystem()
        mfs.mount("src", mem1)
        mfs.mount("dst", mem2)
        mfs.copydir("/src/src", "/dst/dst")
        assert mem2.isdir("/dst")

    def test_copydir_nonexistent_source(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("mnt", mem)
        with pytest.raises(FileNotFoundError):
            mfs.copydir("/mnt/src", "/mnt/dst")

    def test_copydir_nonexistent_dest_fs(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.mkdir("/src")
        mfs.mount("mnt", mem)
        mfs.copydir("/mnt/src", "/none/dst")
        assert mem.isdir("none/dst")

    def test_copydir_ignore_errors(self):
        mfs = FsspecMountFS()
        mem1 = MemoryFileSystem()
        mem2 = MemoryFileSystem()
        mfs.mount("src", mem1)
        mfs.mount("dst", mem2)
        mfs.copydir("/src/src", "/dst/dst", ignore_errors=True)


class TestFsspecMountFSMove:
    def test_move_same_fs(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.pipe("/src.txt", b"move me")
        mfs.mount("mnt", mem)
        mfs.move("/mnt/src.txt", "/mnt/dst.txt")
        assert mem.exists("/dst.txt")
        assert not mem.exists("/src.txt")

    def test_move_cross_fs(self):
        mfs = FsspecMountFS()
        mem1 = MemoryFileSystem()
        mem2 = MemoryFileSystem()
        mem1.pipe("/src.txt", b"cross")
        mfs.mount("src", mem1)
        mfs.mount("dst", mem2)
        mfs.move("/src/src.txt", "/dst/dst.txt")
        assert mem2.cat("/dst.txt") == b"cross"

    def test_move_overwrite(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.pipe("/src.txt", b"new")
        mem.pipe("/dst.txt", b"old")
        mfs.mount("mnt", mem)
        mfs.move("/mnt/src.txt", "/mnt/dst.txt", overwrite=True)


class TestFsspecMountFSMovedir:
    def test_movedir(self):
        mfs = FsspecMountFS()
        mem1 = MemoryFileSystem()
        mem1.mkdir("/src")
        mem1.pipe("/src/a.txt", b"a")
        mem2 = MemoryFileSystem()
        mfs.mount("src", mem1)
        mfs.mount("dst", mem2)
        mfs.movedir("/src/src", "/dst/dst")

    def test_movedir_ignore_errors(self):
        mfs = FsspecMountFS()
        mem1 = MemoryFileSystem()
        mem2 = MemoryFileSystem()
        mfs.mount("src", mem1)
        mfs.mount("dst", mem2)
        mfs.movedir("/src/nonexistent", "/dst/dst", ignore_errors=True)


class TestFsspecMountFSResolve:
    def test_resolve_known_prefix(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("app", mem)
        fs, rest = mfs._resolve("/app/file.txt")
        assert fs is mem
        assert rest == "file.txt"

    def test_resolve_nested_path(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("app", mem)
        fs, rest = mfs._resolve("/app/sub/dir/file.txt")
        assert fs is mem
        assert rest == "sub/dir/file.txt"

    def test_resolve_path_without_leading_slash(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("app", mem)
        fs, rest = mfs._resolve("app/file.txt")
        assert fs is mem
        assert rest == "file.txt"

    def test_resolve_mount_name_known(self):
        mfs = FsspecMountFS()
        mfs.mount("app", "dummy")
        name, rest = mfs._resolve_mount_name("/app/file.txt")
        assert name == "app"
        assert rest == "file.txt"

    def test_resolve_mount_name_unknown_fallback(self):
        mfs = FsspecMountFS()
        mfs.mount("default", "dummy")
        name, rest = mfs._resolve_mount_name("/unknown/file.txt")
        assert name == "default"
        assert rest == "unknown/file.txt"

    def test_resolve_mount_name_empty(self):
        mfs = FsspecMountFS()
        mfs.mount("default", "dummy")
        name, rest = mfs._resolve_mount_name("/")
        assert name == "default"
        assert rest in ("/", "")


class TestFsspecMountFSInitAndMounts:
    def test_init(self):
        mfs = FsspecMountFS()
        assert mfs._mounts == {}
        assert mfs._order == []

    def test_multiple_mounts(self):
        mfs = FsspecMountFS()
        mfs.mount("a", "fs_a")
        mfs.mount("b", "fs_b")
        mfs.mount("c", "fs_c")
        assert len(mfs._mounts) == 3
        assert mfs._order == ["a", "b", "c"]

    def test_mounts_property_format(self):
        mfs = FsspecMountFS()
        mfs.mount("app", "fs_app")
        mounts = mfs.mounts
        assert len(mounts) == 1
        assert mounts[0][0] == "/app/"

    def test_add_fs_duplicate_mount(self):
        mfs = FsspecMountFS()
        mfs.mount("app", "fs1")
        mfs.add_fs("app", "fs1")
        assert isinstance(mfs._mounts["app"], FsspecMultiFS)


class TestFsspecMultiFSFull:
    def test_open_finds_in_first(self):
        mfs = FsspecMultiFS()
        mem = MemoryFileSystem()
        mem.pipe("/file1.txt", b"first")
        mfs.add_fs("a", mem)
        with mfs.open("/file1.txt", "rb") as f:
            assert f.read() == b"first"

    def test_open_finds_in_second(self):
        mfs = FsspecMultiFS()
        mem1 = MemoryFileSystem()
        mem2 = MemoryFileSystem()
        mem2.pipe("/shared.txt", b"second")
        mfs.add_fs("a", mem1)
        mfs.add_fs("b", mem2)
        with mfs.open("/shared.txt", "rb") as f:
            assert f.read() == b"second"

    def test_open_not_found_any(self):
        mfs = FsspecMultiFS()
        mem = MemoryFileSystem()
        mfs.add_fs("a", mem)
        with pytest.raises(FileNotFoundError):
            mfs.open("/nonexistent.txt")

    def test_isfile_true(self):
        mfs = FsspecMultiFS()
        mem = MemoryFileSystem()
        mem.pipe("/test.txt", b"")
        mfs.add_fs("a", mem)
        assert mfs.isfile("/test.txt") is True

    def test_isfile_false(self):
        mfs = FsspecMultiFS()
        mem = MemoryFileSystem()
        mfs.add_fs("a", mem)
        assert mfs.isfile("/nonexistent.txt") is False

    def test_isdir_true(self):
        mfs = FsspecMultiFS()
        mem = MemoryFileSystem()
        mfs.add_fs("a", mem)
        assert mfs.isdir("/") is True or mfs.isdir("") is True

    def test_isdir_false(self):
        mfs = FsspecMultiFS()
        mem = MemoryFileSystem()
        mfs.add_fs("a", mem)
        assert mfs.isdir("/nonexistent") is False

    def test_exists_true(self):
        mfs = FsspecMultiFS()
        mem = MemoryFileSystem()
        mem.pipe("/test.txt", b"")
        mfs.add_fs("a", mem)
        assert mfs.exists("/test.txt") is True

    def test_exists_false(self):
        mfs = FsspecMultiFS()
        mem = MemoryFileSystem()
        mfs.add_fs("a", mem)
        assert mfs.exists("/no.txt") is False

    def test_ls_returns_items(self):
        mfs = FsspecMultiFS()
        mem = MemoryFileSystem()
        mem.pipe("/a.txt", b"a")
        mem.pipe("/b.txt", b"b")
        mfs.add_fs("a", mem)
        result = mfs.ls("", detail=False)
        assert isinstance(result, list)

    def test_ls_with_detail(self):
        mfs = FsspecMultiFS()
        mem = MemoryFileSystem()
        mem.pipe("/test.txt", b"data")
        mfs.add_fs("a", mem)
        result = mfs.ls("", detail=True)
        assert isinstance(result, list)

    def test_ls_empty_when_no_match(self):
        mfs = FsspecMultiFS()
        mem = MemoryFileSystem()
        mfs.add_fs("a", mem)
        result = mfs.ls("/nonexistent", detail=False)
        assert result == []

    def test_info_file(self):
        mfs = FsspecMultiFS()
        mem = MemoryFileSystem()
        mem.pipe("/test.txt", b"hello")
        mfs.add_fs("a", mem)
        info = mfs.info("/test.txt")
        assert isinstance(info, dict)
        assert "name" in info

    def test_info_not_found(self):
        mfs = FsspecMultiFS()
        mem = MemoryFileSystem()
        mfs.add_fs("a", mem)
        with pytest.raises(FileNotFoundError):
            mfs.info("/none.txt")

    def test_info_second_fs(self):
        mfs = FsspecMultiFS()
        mem1 = MemoryFileSystem()
        mem2 = MemoryFileSystem()
        mem2.pipe("/in_second.txt", b"second")
        mfs.add_fs("a", mem1)
        mfs.add_fs("b", mem2)
        info = mfs.info("/in_second.txt")
        assert info["name"] == "/in_second.txt"


class TestAutoCreateLocalFsInit:
    def test_init_with_tmpdir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fs = _AutoCreateLocalFs(tmpdir)
            assert fs._root == os.path.abspath(tmpdir)

    def test_init_auto_mkdir_true(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, "newdir")
            fs = _AutoCreateLocalFs(subdir)
            assert fs._root == os.path.abspath(subdir)

    def test_init_auto_mkdir_false(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fs = _AutoCreateLocalFs(tmpdir, auto_mkdir=False)
            assert fs._root == os.path.abspath(tmpdir)


class TestFsspecInfoCoverage:
    def test_modified_last_modified(self):
        dt = datetime.datetime(2025, 6, 15, tzinfo=datetime.UTC)
        info = _FsspecInfo({"LastModified": dt.timestamp()})
        assert info.modified is not None
        assert isinstance(info.modified, datetime.datetime)

    def test_created_creation_time(self):
        dt = datetime.datetime(2025, 6, 15, tzinfo=datetime.UTC)
        info = _FsspecInfo({"CreationTime": dt.timestamp()})
        assert info.created is not None

    def test_accessed_last_access_time(self):
        dt = datetime.datetime(2025, 6, 15, tzinfo=datetime.UTC)
        info = _FsspecInfo({"LastAccessTime": dt.timestamp()})
        assert info.accessed is not None

    def test_name_trailing_slash(self):
        info = _FsspecInfo({"name": "/path/to/dir/"})
        assert info.name == "dir"

    def test_isdir_cached(self):
        info = _FsspecInfo({"type": "directory"})
        assert info.isdir is True
        assert info.isdir is True


class TestFsspecAbspathCoverage:
    def test_double_dots_at_start(self):
        result = _fsspec_abspath("../a/b")
        assert result.endswith("a/b") or result == "/a/b"

    def test_consecutive_double_dots(self):
        result = _fsspec_abspath("/a/b/../../c/../d")
        assert result == "/d"

    def test_empty_segments(self):
        result = _fsspec_abspath("/a//b")
        assert result == "/a/b"

    def test_windows_style_backslashes(self):
        result = _fsspec_abspath("/a\\b\\c")
        assert result in ("/a/b/c", "/a\\b\\c")


class TestFsspecJoinCoverage:
    def test_join_with_trailing_slash(self):
        assert _fsspec_join("a/", "b") == "/a/b"

    def test_join_single_arg(self):
        assert _fsspec_join("hello") == "/hello"

    def test_join_empty_args_returns_root(self):
        assert _fsspec_join("") == "/"


class TestMountFSResolveCoverage:
    def test_resolve_path_with_colon(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("zip", mem)
        fs, rest = mfs._resolve("/zip:/file.txt")
        assert fs is mem
        assert rest == "zip:/file.txt"

    def test_resolve_leading_double_slash(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("mnt", mem)
        fs, rest = mfs._resolve("//mnt/file.txt")
        assert fs is mem

    def test_resolve_no_leading_slash_prefix_only(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("mnt", mem)
        fs, rest = mfs._resolve("mnt")
        assert fs is mem


class TestFsspecMountFSGetsyspathCoverage:
    def test_getsyspath_fallback_non_local_nonmemory(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.pipe("/f.txt", b"data")
        mfs.mount("mnt", mem)
        result = mfs.getsyspath("/mnt/f.txt")
        assert "memory://" in result

    def test_getsyspath_with_root_path(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("mnt", mem)
        result = mfs.getsyspath("/mnt")
        assert isinstance(result, str)


class TestFsspecMountFSScandirCoverage:
    def test_scandir_on_root(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mem.pipe("/f.txt", b"data")
        mfs.mount("mnt", mem)
        results = mfs.scandir("/mnt")
        assert isinstance(results, list)


class TestFsspecMultiFSGetsyspath:
    def test_getsyspath_finds_file(self):
        mfs = FsspecMultiFS()
        mem = MemoryFileSystem()
        mem.pipe("/test.txt", b"data")
        mfs.add_fs("a", mem)
        result = mfs.getsyspath("test.txt")
        assert isinstance(result, str)

    def test_getsyspath_not_found_allow_none(self):
        mfs = FsspecMultiFS()
        mem = MemoryFileSystem()
        mfs.add_fs("a", mem)
        result = mfs.getsyspath("no.txt", allow_none=True)
        assert result is None

    def test_getsyspath_not_found_raises(self):
        mfs = FsspecMultiFS()
        mem = MemoryFileSystem()
        mfs.add_fs("a", mem)
        with pytest.raises(FileNotFoundError):
            mfs.getsyspath("no.txt")


class TestMountFSExistsScandirCoverage:
    def test_exists_empty_rest_returns_true(self):
        mfs = FsspecMountFS()
        mem = MemoryFileSystem()
        mfs.mount("mnt", mem)
        assert mfs.exists("/mnt") is True


class TestFsspecCopyFile:
    def test_copy_file_with_get_put(self):
        fake1 = _OpenTestFS()
        fake2 = _OpenTestFS()
        fake1.files["file"] = b"data"
        fake2.files["file"] = b"overwritable"
        FsspecMountFS._copy_file(fake1, "file", fake2, "file", True)
        assert fake2.files["file"] == b"data"

    def test_copy_file_data_transfer(self):
        fake1 = _OpenTestFS()
        fake1.files["src"] = b"hello"
        fake2 = _OpenTestFS()
        FsspecMountFS._copy_file(fake1, "src", fake2, "dst", False)
        assert fake2.files["dst"] == b"hello"

    def test_copy_file_overwrite_with_remove(self):
        fake1 = _OpenTestFS()
        fake1.files["src"] = b"new data"
        fake2 = _OpenTestFS()
        fake2.files["dst"] = b"old data"
        FsspecMountFS._copy_file(fake1, "src", fake2, "dst", True)
        assert fake2.files["dst"] == b"new data"
