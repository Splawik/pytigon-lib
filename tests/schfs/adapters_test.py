"""Behavioural tests for the fsspec-based adapters (schfs.adapters)."""

import pytest

from pytigon_lib.schfs.adapters import (
    FsspecMountFS,
    FsspecMultiFS,
    FsspecSimpleFS,
    _normalise_path,
)


def _simple(tmp_path, name="root"):
    """A FsspecSimpleFS with an existing root and no instance caching."""
    root = tmp_path / name
    root.mkdir()
    return FsspecSimpleFS(str(root), skip_instance_cache=True), root


class TestNormalisePath:
    def test_empty_values(self):
        assert _normalise_path(None) == ""
        assert _normalise_path("") == ""
        assert _normalise_path(".") == ""
        assert _normalise_path("/") == ""

    def test_normalises_separators_and_dots(self):
        assert _normalise_path("/a/b/") == "a/b"
        assert _normalise_path("a//b/./c") == "a/b/c"
        assert _normalise_path("a\\b") == "a/b"

    def test_rejects_escape(self):
        with pytest.raises(ValueError):
            _normalise_path("../secret")
        with pytest.raises(ValueError):
            _normalise_path("a/../../secret")
        with pytest.raises(ValueError):
            _normalise_path("..")


class TestFsspecSimpleFS:
    def test_write_read_roundtrip(self, tmp_path):
        fs, _root = _simple(tmp_path)
        with fs.open("dir/file.txt", "wb") as handle:
            handle.write(b"hello")
        assert fs.exists("dir/file.txt")
        with fs.open("dir/file.txt", "rb") as handle:
            assert handle.read() == b"hello"

    def test_paths_are_confined_to_root(self, tmp_path):
        fs, root = _simple(tmp_path)
        with fs.open("a.txt", "wb") as handle:
            handle.write(b"x")
        assert (root / "a.txt").read_bytes() == b"x"

    def test_escape_is_rejected(self, tmp_path):
        fs, _root = _simple(tmp_path)
        with pytest.raises(ValueError):
            fs.open("../escape.txt", "wb")

    def test_ls_returns_logical_names(self, tmp_path):
        fs, _root = _simple(tmp_path)
        with fs.open("a.txt", "wb") as handle:
            handle.write(b"x")
        names = fs.ls("", detail=False)
        assert "a.txt" in names

    def test_rm(self, tmp_path):
        fs, _root = _simple(tmp_path)
        with fs.open("a.txt", "wb") as handle:
            handle.write(b"x")
        fs.rm("a.txt")
        assert not fs.exists("a.txt")


class TestFsspecMultiFS:
    def _two_layers(self, tmp_path):
        first = tmp_path / "first"
        second = tmp_path / "second"
        first.mkdir()
        second.mkdir()
        fs = FsspecMultiFS(skip_instance_cache=True)
        fs.add_fs("first", str(first))
        fs.add_fs("second", str(second))
        return fs, first, second

    def test_write_goes_to_first_layer(self, tmp_path):
        fs, first, second = self._two_layers(tmp_path)
        with fs.open("data.txt", "wb") as handle:
            handle.write(b"first-value")
        assert (first / "data.txt").read_bytes() == b"first-value"
        assert not (second / "data.txt").exists()

    def test_read_prefers_first_layer(self, tmp_path):
        fs, first, second = self._two_layers(tmp_path)
        (first / "shared.txt").write_bytes(b"first")
        (second / "shared.txt").write_bytes(b"second")
        with fs.open("shared.txt", "rb") as handle:
            assert handle.read() == b"first"

    def test_read_falls_back_to_second_layer(self, tmp_path):
        fs, _first, second = self._two_layers(tmp_path)
        (second / "only.txt").write_bytes(b"second")
        with fs.open("only.txt", "rb") as handle:
            assert handle.read() == b"second"

    def test_missing_file_raises(self, tmp_path):
        fs, _first, _second = self._two_layers(tmp_path)
        with pytest.raises(FileNotFoundError):
            fs.open("nope.txt", "rb")

    def test_duplicate_name_is_rejected(self, tmp_path):
        fs, first, _second = self._two_layers(tmp_path)
        with pytest.raises(ValueError):
            fs.add_fs("first", str(first))

    def test_write_without_layers_raises(self):
        fs = FsspecMultiFS(skip_instance_cache=True)
        with pytest.raises(RuntimeError):
            fs.open("a.txt", "wb")


class TestFsspecMountFS:
    def _mounted(self, tmp_path, mounts=("data",)):
        fs = FsspecMountFS(skip_instance_cache=True)
        for name in mounts:
            (tmp_path / name).mkdir()
            fs.mount(name, str(tmp_path / name))
        return fs

    def test_mount_read_write(self, tmp_path):
        fs = self._mounted(tmp_path, ("data",))
        with fs.open("data/x.txt", "wb") as handle:
            handle.write(b"x")
        assert fs.exists("data/x.txt")
        with fs.open("data/x.txt", "rb") as handle:
            assert handle.read() == b"x"

    def test_ls_lists_virtual_mount_directories(self, tmp_path):
        fs = self._mounted(tmp_path, ("alpha", "beta"))
        names = fs.ls("", detail=False)
        assert "alpha" in names
        assert "beta" in names

    def test_unmounted_path_raises(self):
        fs = FsspecMountFS(skip_instance_cache=True)
        with pytest.raises(FileNotFoundError):
            fs.open("nope/x.txt", "rb")

    def test_mount_root_cannot_be_removed(self, tmp_path):
        fs = self._mounted(tmp_path, ("alpha",))
        with pytest.raises(PermissionError):
            fs.rm("alpha", recursive=True)

    def test_duplicate_mount_is_rejected(self, tmp_path):
        fs = self._mounted(tmp_path, ("alpha",))
        (tmp_path / "beta").mkdir()
        with pytest.raises(ValueError):
            fs.mount("alpha", str(tmp_path / "beta"))

    def test_unmount(self, tmp_path):
        fs = self._mounted(tmp_path, ("alpha",))
        fs.unmount("alpha")
        assert fs.mounts == ()
