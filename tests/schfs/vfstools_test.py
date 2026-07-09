import os
import io
import tempfile
import zipfile
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schfs.vfstools import (
    ZipWriter,
    _clear_content,
    _cmp_txt_str_content,
    _is_safe_zip_path,
    automount,
    convert_file,
    delete_from_zip,
    extractall,
    get_temp_filename,
    get_unique_filename,
    norm_path,
    open_and_create_dir,
    open_file,
)


class TestNormPath:
    def test_simple_dotdot(self):
        assert norm_path("a/b/../c") == "a/c"

    def test_simple_dot(self):
        assert norm_path("a/b/./c") == "a/b/c"

    def test_multiple_dotdot(self):
        assert norm_path("a/b/../../c") == "c"

    def test_empty_string(self):
        assert norm_path("") == ""

    def test_none_input(self):
        assert norm_path(None) == ""

    def test_no_dots(self):
        assert norm_path("a/b/c/d") == "a/b/c/d"

    def test_leading_dotdot_root(self):
        assert norm_path("../a/b") == "a/b"

    def test_starts_with_dot_string(self):
        assert norm_path("./x/../y") == "y"

    def test_protocol_prefix(self):
        assert norm_path("http://example.com/a/b/../c") == "http://example.com/a/c"

    def test_space_in_path(self):
        assert norm_path("a/b c/d/../e") == "a/b c/e"

    def test_backslashes(self):
        assert norm_path("a\\b\\..\\c") == "a/c"

    def test_dotdot_takes_to_root(self):
        assert norm_path("a/..") == ""


class TestOpenFile:
    def test_open_write_read(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            pass
        try:
            with open_file(tmp.name, "w") as f:
                f.write("test")
            with open_file(tmp.name, "r") as f:
                assert f.read() == "test"
        finally:
            os.unlink(tmp.name)

    def test_open_for_vfs(self):
        mock_fs = MagicMock()
        with patch("pytigon_lib.schfs.vfstools.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            open_file("/vfs/test.txt", "r", for_vfs=True)
            mock_fs.open.assert_called_once_with("/vfs/test.txt", "r")


class TestOpenAndCreateDir:
    def test_creates_intermediate_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "subdir", "test.txt")
            with open_and_create_dir(file_path, "w") as f:
                f.write("test")
            assert os.path.exists(file_path)
            with open(file_path) as f:
                assert f.read() == "test"

    def test_existing_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test.txt")
            with open_and_create_dir(file_path, "w") as f:
                f.write("existing")
            assert os.path.exists(file_path)


class TestGetUniqueFilename:
    def test_has_base_name(self):
        filename = get_unique_filename("base", "txt")
        assert "base" in filename
        assert "txt" in filename

    def test_no_params(self):
        filename = get_unique_filename()
        assert isinstance(filename, str)
        assert len(filename) > 0

    def test_only_base(self):
        filename = get_unique_filename("report")
        assert "report" in filename
        assert "." not in filename

    def test_only_ext(self):
        filename = get_unique_filename(ext="csv")
        assert filename.endswith(".csv")


class TestGetTempFilename:
    def test_has_base_and_ext(self):
        filename = get_temp_filename("base", "txt")
        assert "base" in filename
        assert "txt" in filename

    def test_for_vfs(self):
        filename = get_temp_filename("base", "txt", for_vfs=True)
        assert filename.startswith("/temp/")
        assert "base" in filename

    def test_no_params(self):
        filename = get_temp_filename()
        assert isinstance(filename, str)


class TestDeleteFromZip:
    def test_deletes_single_file(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            with zipfile.ZipFile(tmp.name, "w") as zf:
                zf.writestr("test.txt", b"content")
            delete_from_zip(tmp.name, ["test.txt"])
            with zipfile.ZipFile(tmp.name, "r") as zf:
                assert "test.txt" not in zf.namelist()

    def test_case_insensitive_deletion(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            with zipfile.ZipFile(tmp.name, "w") as zf:
                zf.writestr("File.TXT", b"content")
                zf.writestr("other.bin", b"data")
            delete_from_zip(tmp.name, ["file.txt"])
            with zipfile.ZipFile(tmp.name, "r") as zf:
                names = [n.lower() for n in zf.namelist()]
                assert "file.txt" not in names
                assert "other.bin" in names

    def test_keeps_unmatched_files(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            with zipfile.ZipFile(tmp.name, "w") as zf:
                zf.writestr("keep.txt", b"keep")
                zf.writestr("del.txt", b"del")
            delete_from_zip(tmp.name, ["del.txt"])
            with zipfile.ZipFile(tmp.name, "r") as zf:
                assert "keep.txt" in zf.namelist()
                assert "del.txt" not in zf.namelist()

    def test_delete_multiple_files(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            with zipfile.ZipFile(tmp.name, "w") as zf:
                zf.writestr("a.txt", b"a")
                zf.writestr("b.txt", b"b")
                zf.writestr("c.txt", b"c")
            delete_from_zip(tmp.name, ["a.txt", "b.txt"])
            with zipfile.ZipFile(tmp.name, "r") as zf:
                assert "c.txt" in zf.namelist()
                assert "a.txt" not in zf.namelist()
                assert "b.txt" not in zf.namelist()

    def test_delete_nonexistent_file(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            with zipfile.ZipFile(tmp.name, "w") as zf:
                zf.writestr("keep.txt", b"keep")
            delete_from_zip(tmp.name, ["nonexistent.txt"])
            with zipfile.ZipFile(tmp.name, "r") as zf:
                assert "keep.txt" in zf.namelist()


class TestExtractall:
    def test_extracts_to_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
                with zipfile.ZipFile(tmp.name, "w") as zf:
                    zf.writestr("test.txt", b"content")
                with zipfile.ZipFile(tmp.name, "r") as zf:
                    extractall(zf, tmpdir)
                assert os.path.exists(os.path.join(tmpdir, "test.txt"))

    def test_exclude_patterns(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
                with zipfile.ZipFile(tmp.name, "w") as zf:
                    zf.writestr("test.txt", b"content")
                    zf.writestr("test.log", b"log")
                with zipfile.ZipFile(tmp.name, "r") as zf:
                    extractall(zf, tmpdir, exclude=[r".*\.log$"])
                assert os.path.exists(os.path.join(tmpdir, "test.txt"))
                assert not os.path.exists(os.path.join(tmpdir, "test.log"))

    def test_only_path_filter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
                with zipfile.ZipFile(tmp.name, "w") as zf:
                    zf.writestr("sub/test.txt", b"content")
                    zf.writestr("other.txt", b"other")
                with zipfile.ZipFile(tmp.name, "r") as zf:
                    extractall(zf, tmpdir, only_path="sub")
                assert os.path.exists(os.path.join(tmpdir, "sub", "test.txt"))
                assert not os.path.exists(os.path.join(tmpdir, "other.txt"))

    def test_directory_entry(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
                with zipfile.ZipFile(tmp.name, "w") as zf:
                    zf.writestr("dir/", b"")
                    zf.writestr("dir/test.txt", b"content")
                with zipfile.ZipFile(tmp.name, "r") as zf:
                    extractall(zf, tmpdir)
                assert os.path.isdir(os.path.join(tmpdir, "dir"))

    def test_path_none(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
                with zipfile.ZipFile(tmp.name, "w") as zf:
                    zf.writestr("test.txt", b"content")
                with zipfile.ZipFile(tmp.name, "r") as zf:
                    extractall(zf)
                    assert os.path.exists("test.txt")
                os.unlink("test.txt")

    def test_specific_members(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
                with zipfile.ZipFile(tmp.name, "w") as zf:
                    zf.writestr("a.txt", b"a")
                    zf.writestr("b.txt", b"b")
                with zipfile.ZipFile(tmp.name, "r") as zf:
                    extractall(zf, tmpdir, members=["a.txt"])
                assert os.path.exists(os.path.join(tmpdir, "a.txt"))
                assert not os.path.exists(os.path.join(tmpdir, "b.txt"))

    def test_backup_zip_writes_old_content(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.NamedTemporaryFile(suffix=".zip") as src_tmp:
                with zipfile.ZipFile(src_tmp.name, "w") as zf:
                    zf.writestr("test.txt", b"new content")
                os.makedirs(tmpdir, exist_ok=True)
                old_path = os.path.join(tmpdir, "test.txt")
                with open(old_path, "w") as f:
                    f.write("old content")
                with tempfile.NamedTemporaryFile(suffix=".zip") as backup_tmp:
                    with zipfile.ZipFile(src_tmp.name, "r") as zf_src:
                        with zipfile.ZipFile(backup_tmp.name, "w") as backup_zf:
                            extractall(zf_src, tmpdir, backup_zip=backup_zf)
                    with zipfile.ZipFile(backup_tmp.name, "r") as zf:
                        assert "test.txt" in zf.namelist()
                        assert zf.read("test.txt") == b"old content"

    def test_zip_slip_prevention(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfilename = os.path.join(tmpdir, "evil.zip")
            with zipfile.ZipFile(tmpfilename, "w") as zf:
                zf.writestr("../outside.txt", b"evil")
            with zipfile.ZipFile(tmpfilename, "r") as zf:
                with patch("pytigon_lib.schfs.vfstools.logger.warning") as mock_warn:
                    extractall(zf, tmpdir)
                    mock_warn.assert_called()
            assert not os.path.exists(os.path.join(tmpdir, "..", "outside.txt"))


class TestZipWriter:
    def test_writestr(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            writer = ZipWriter(tmp.name)
            writer.writestr("test.txt", b"content")
            writer.close()
            with zipfile.ZipFile(tmp.name, "r") as zf:
                assert "test.txt" in zf.namelist()

    def test_write_with_name_in_zip(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            src = tempfile.NamedTemporaryFile(delete=False)
            src.write(b"data")
            src.close()
            try:
                writer = ZipWriter(tmp.name)
                writer.write(src.name, name_in_zip="custom.txt")
                writer.close()
                with zipfile.ZipFile(tmp.name, "r") as zf:
                    assert "custom.txt" in zf.namelist()
            finally:
                os.unlink(src.name)

    def test_write_exclude_pattern(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            src = tempfile.NamedTemporaryFile(suffix=".log", delete=False)
            src.write(b"logdata")
            src.close()
            try:
                writer = ZipWriter(tmp.name, exclude=[r".*\.log$"])
                writer.write(src.name)
                writer.close()
                with zipfile.ZipFile(tmp.name, "r") as zf:
                    assert zf.namelist() == []
            finally:
                os.unlink(src.name)

    def test_sha256_tracking(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            writer = ZipWriter(tmp.name, sha256=True)
            writer.writestr("test.txt", b"hello")
            writer.close()
            assert len(writer.sha256_tab) == 1
            assert writer.sha256_tab[0][0] == "test.txt"
            assert len(writer.sha256_tab[0][1]) == 64
            assert writer.sha256_tab[0][2] == 5

    def test_basepath_stripping(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            os.makedirs(os.path.join(tmpdir, "sub"), exist_ok=True)
            src = os.path.join(tmpdir, "sub", "file.txt")
            with open(src, "w") as f:
                f.write("data")
            zip_path = os.path.join(tmpdir, "out.zip")
            writer = ZipWriter(zip_path, basepath=tmpdir)
            writer.write(src)
            writer.close()
            with zipfile.ZipFile(zip_path, "r") as zf:
                assert "sub/file.txt" in zf.namelist()

    def test_strip_base_exact(self):
        writer = ZipWriter("/tmp/test.zip", basepath="/home/user")
        result = writer._strip_base("/home/user/data/file.txt")
        assert result == "data/file.txt"

    def test_strip_base_not_under(self):
        writer = ZipWriter("/tmp/test.zip", basepath="/home/user")
        result = writer._strip_base("/other/file.txt")
        assert result == "/other/file.txt"


class TestClearContent:
    def test_removes_whitespace(self):
        assert _clear_content(b"a b\nc\td\re") == b"abcde"

    def test_no_whitespace(self):
        assert _clear_content(b"abc") == b"abc"


class TestCmpTxtStrContent:
    def test_same_after_stripping(self):
        assert _cmp_txt_str_content(b"a b c", b"abc")

    def test_different(self):
        assert not _cmp_txt_str_content(b"abc", b"abd")


class TestIsSafeZipPath:
    def test_safe_path(self):
        assert _is_safe_zip_path("file.txt", "/tmp/extract")

    def test_unsafe_path(self):
        assert not _is_safe_zip_path("../file.txt", "/tmp/extract")

    def test_safe_nested(self):
        assert _is_safe_zip_path("sub/dir/file.txt", "/tmp/extract")


class TestConvertFile:
    def test_md_to_html_local(self):
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as src:
            src.write("# Hello\n\nWorld")
            src.flush()
        try:
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as dst:
                pass
            try:
                assert convert_file(
                    src.name,
                    dst.name,
                    input_format="md",
                    output_format="html",
                    for_vfs_input=False,
                    for_vfs_output=False,
                )
                with open(dst.name) as f:
                    content = f.read()
                    assert "<h1>" in content or "<p>" in content
            finally:
                os.unlink(dst.name)
        finally:
            os.unlink(src.name)


class TestAutomount:
    def test_non_zip_path_returns_unchanged(self):
        assert automount("/data/file.txt") == "/data/file.txt"

    def test_no_zip_in_path(self):
        assert automount("/data/archive") == "/data/archive"

    def test_path_without_zip_returns_unchanged(self):
        assert automount("/tmp/something") == "/tmp/something"
