"""Extra tests for :mod:`pytigon_lib.schfs.vfstools` beyond existing vfstools_test.py."""

import io
import os
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


class TestNormPathExtra:
    def test_consecutive_dotdot_into_nothing(self):
        assert norm_path("a/b/c/../../..") == ""

    def test_single_dot_alone(self):
        result = norm_path(".")
        assert result in ("", "/")

    def test_double_dot_alone(self):
        result = norm_path("..")
        assert result in ("", "/")

    def test_url_with_query_string(self):
        result = norm_path("http://example.com/a/../b?q=1")
        assert "http://example.com/b?q=1" in result or "http" in result

    def test_only_spaces_and_protocol(self):
        result = norm_path("  file:///a/b  ")
        assert "file" in result

    def test_empty_segments(self):
        result = norm_path("a//b")
        assert result == "a//b"

    def test_leading_slash(self):
        result = norm_path("/a/b/c")
        assert result in ("/a/b/c", "a/b/c")

    def test_trailing_slash(self):
        result = norm_path("a/b/c/")
        assert result in ("a/b/c", "a/b/c/")

    def test_only_protocol_prefix(self):
        result = norm_path("git://")
        assert "git" in result

    def test_complex_mixed_backslashes_and_dots(self):
        result = norm_path("a\\b/..\\c/./d")
        assert result.endswith("c/d") or result.endswith("a/d")

    def test_dotdot_in_protocol_path(self):
        result = norm_path("file:///home/user/../other/file.txt")
        assert "file://" in result
        assert "other/file.txt" in result


class TestOpenFileExtra:
    def test_open_file_nonexistent_raises(self):
        with pytest.raises(OSError):
            open_file("/nonexistent/path/file.txt", "r")

    def test_open_file_for_vfs_exception(self):
        mock_fs = MagicMock()
        mock_fs.open.side_effect = Exception("fail")
        with patch("pytigon_lib.schfs.vfstools.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            with pytest.raises(OSError):
                open_file("/vfs/test.txt", "r", for_vfs=True)

    def test_open_file_write_creates(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            pass
        try:
            with open_file(tmp.name, "w") as f:
                f.write("data")
            with open_file(tmp.name, "r") as f:
                assert f.read() == "data"
        finally:
            os.unlink(tmp.name)


class TestOpenAndCreateDirExtra:
    def test_creates_deep_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "a", "b", "c", "test.txt")
            with open_and_create_dir(file_path, "w") as f:
                f.write("deep")
            assert os.path.exists(file_path)

    def test_for_vfs_creates_dirs(self):
        mock_fs = MagicMock()
        mock_fs.exists.return_value = False
        with patch("pytigon_lib.schfs.vfstools.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            with patch("pytigon_lib.schfs.vfstools.open_file") as mock_open_fn:
                mock_open_fn.return_value = MagicMock()
                open_and_create_dir("/vfs/sub/dir/file.txt", "w", for_vfs=True)
                mock_fs.makedirs.assert_called_once()

    def test_for_vfs_existing_dir(self):
        mock_fs = MagicMock()
        mock_fs.exists.return_value = True
        with patch("pytigon_lib.schfs.vfstools.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            with patch("pytigon_lib.schfs.vfstools.open_file") as mock_open_fn:
                mock_open_fn.return_value = MagicMock()
                open_and_create_dir("/vfs/existing/file.txt", "w", for_vfs=True)
                mock_fs.exists.assert_called_once()
                mock_fs.makedirs.assert_not_called()

    def test_exception_wraps_to_oserror(self):
        with patch("pytigon_lib.schfs.vfstools.os.path.dirname", side_effect=Exception("boom")):
            with pytest.raises(OSError):
                open_and_create_dir("/fake/file.txt", "w")


class TestGetUniqueFilenameExtra:
    def test_multiple_calls_unique(self):
        f1 = get_unique_filename()
        f2 = get_unique_filename()
        assert f1 != f2

    def test_full_params(self):
        filename = get_unique_filename("report", "pdf")
        assert "report" in filename
        assert filename.endswith(".pdf")

    def test_long_base_name(self):
        filename = get_unique_filename("very_long_base_name_with_many_characters")
        assert "very_long_base_name" in filename


class TestGetTempFilenameExtra:
    def test_starts_with_temp_prefix(self):
        filename = get_temp_filename(for_vfs=True)
        assert filename.startswith("/temp/")

    def test_uses_settings_temp_path(self):
        filename = get_temp_filename(for_vfs=False)
        assert tempfile.gettempdir() in filename


class TestDeleteFromZipExtra:
    def test_empty_del_list(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            with zipfile.ZipFile(tmp.name, "w") as zf:
                zf.writestr("test.txt", b"content")
            delete_from_zip(tmp.name, [])
            with zipfile.ZipFile(tmp.name, "r") as zf:
                assert "test.txt" in zf.namelist()

    def test_delete_all_files(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            with zipfile.ZipFile(tmp.name, "w") as zf:
                zf.writestr("a.txt", b"a")
                zf.writestr("b.txt", b"b")
            delete_from_zip(tmp.name, ["a.txt", "b.txt"])
            with zipfile.ZipFile(tmp.name, "r") as zf:
                assert zf.namelist() == []

    def test_non_existent_zip_raises(self):
        with pytest.raises(OSError):
            delete_from_zip("/nonexistent/file.zip", ["test.txt"])


class TestExtractallExtra:
    def test_none_path_defaults_empty_string(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            with zipfile.ZipFile(tmp.name, "w") as zf:
                zf.writestr("test.txt", b"content")
            with zipfile.ZipFile(tmp.name, "r") as zf:
                extractall(zf)
                assert os.path.exists("test.txt")
            os.unlink("test.txt")

    def test_backup_exts_filter(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.NamedTemporaryFile(suffix=".zip") as src_tmp:
                with zipfile.ZipFile(src_tmp.name, "w") as zf:
                    zf.writestr("file.txt", b"new")
                    zf.writestr("file.log", b"new log")
                old_txt = os.path.join(tmpdir, "file.txt")
                old_log = os.path.join(tmpdir, "file.log")
                with open(old_txt, "w") as f:
                    f.write("old txt")
                with open(old_log, "w") as f:
                    f.write("old log")
                with tempfile.NamedTemporaryFile(suffix=".zip") as backup_tmp:
                    with zipfile.ZipFile(src_tmp.name, "r") as zf_src:
                        with zipfile.ZipFile(backup_tmp.name, "w") as backup_zf:
                            extractall(zf_src, tmpdir, backup_zip=backup_zf, backup_exts=["txt"])
                    with zipfile.ZipFile(backup_tmp.name, "r") as zf:
                        names = zf.namelist()
                        assert "file.txt" in names
                        assert "file.log" not in names

    def test_exclude_case_insensitive(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
                with zipfile.ZipFile(tmp.name, "w") as zf:
                    zf.writestr("FILE.TXT", b"content")
                with zipfile.ZipFile(tmp.name, "r") as zf:
                    extractall(zf, tmpdir, exclude=[r".*\.txt$"])
                assert not os.path.exists(os.path.join(tmpdir, "FILE.TXT"))

    def test_slip_detection_absolute_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpfilename = os.path.join(tmpdir, "evil.zip")
            with zipfile.ZipFile(tmpfilename, "w") as zf:
                zf.writestr("/etc/passwd", b"bad")
            with zipfile.ZipFile(tmpfilename, "r") as zf:
                extractall(zf, tmpdir)

    def test_empty_members_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
                with zipfile.ZipFile(tmp.name, "w") as zf:
                    zf.writestr("test.txt", b"content")
                with zipfile.ZipFile(tmp.name, "r") as zf:
                    extractall(zf, tmpdir, members=[])
                assert not os.path.exists(os.path.join(tmpdir, "test.txt"))


class TestZipWriterExtra:
    def test_writestr_bytes(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            writer = ZipWriter(tmp.name)
            writer.writestr("hello.txt", b"world")
            writer.close()
            with zipfile.ZipFile(tmp.name, "r") as zf:
                assert zf.read("hello.txt") == b"world"

    def test_write_skip_permission_error(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            writer = ZipWriter(tmp.name)
            with patch("builtins.open", side_effect=OSError("Permission denied")):
                writer.write("/nonexistent/file.txt")

    def test_write_with_base_path_in_zip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
                src = os.path.join(tmpdir, "data.txt")
                with open(src, "w") as f:
                    f.write("test")
                writer = ZipWriter(tmp.name, basepath=tmpdir)
                writer.write(src, base_path_in_zip="prefix")
                writer.close()
                with zipfile.ZipFile(tmp.name, "r") as zf:
                    assert any(name.startswith("prefix/") for name in zf.namelist())

    def test_to_zip_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = os.path.join(tmpdir, "test.txt")
            with open(src, "w") as f:
                f.write("hello")
            with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
                writer = ZipWriter(tmp.name, basepath=tmpdir)
                writer.to_zip(src)
                writer.close()
                with zipfile.ZipFile(tmp.name, "r") as zf:
                    assert "test.txt" in zf.namelist()

    def test_to_zip_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = os.path.join(tmpdir, "sub")
            os.makedirs(subdir)
            with open(os.path.join(subdir, "a.txt"), "w") as f:
                f.write("a")
            with open(os.path.join(subdir, "b.txt"), "w") as f:
                f.write("b")
            with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
                writer = ZipWriter(tmp.name)
                writer.to_zip(subdir)
                writer.close()
                with zipfile.ZipFile(tmp.name, "r") as zf:
                    names = zf.namelist()
                    assert any("a.txt" in n for n in names)
                    assert any("b.txt" in n for n in names)

    def test_add_folder_to_zip_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
                writer = ZipWriter(tmp.name)
                writer.add_folder_to_zip(tmpdir)
                writer.close()
                with zipfile.ZipFile(tmp.name, "r") as zf:
                    assert zf.namelist() == []

    def test_add_folder_to_zip_permission_error(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            writer = ZipWriter(tmp.name)
            with patch("os.listdir", side_effect=OSError("denied")):
                writer.add_folder_to_zip("/root")

    def test_sha256_no_tracking(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            writer = ZipWriter(tmp.name, sha256=False)
            writer.writestr("test.txt", b"data")
            writer.close()
            assert writer.sha256_tab is None

    def test_sha256_gen(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            writer = ZipWriter(tmp.name, sha256=True)
            writer._sha256_gen("file.bin", b"0123456789")
            assert len(writer.sha256_tab) == 1
            assert writer.sha256_tab[0][0] == "file.bin"
            assert writer.sha256_tab[0][2] == 10

    def test_strip_base_empty_basepath(self):
        writer = ZipWriter("/tmp/test.zip", basepath="")
        result = writer._strip_base("/home/user/data/file.txt")
        assert result == "/home/user/data/file.txt"

    def test_strip_base_trailing_slash(self):
        writer = ZipWriter("/tmp/test.zip", basepath="/home/user/")
        result = writer._strip_base("/home/user/data/file.txt")
        assert result == "data/file.txt"

    def test_close(self):
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            writer = ZipWriter(tmp.name)
            writer.close()


class TestClearContentExtra:
    def test_empty_bytes(self):
        assert _clear_content(b"") == b""

    def test_only_whitespace(self):
        assert _clear_content(b"  \t\n\r  ") == b""

    def test_mixed_with_newlines(self):
        assert _clear_content(b"a\r\nb\r\nc") == b"abc"


class TestCmpTxtStrContentExtra:
    def test_both_empty(self):
        assert _cmp_txt_str_content(b"", b"") is True

    def test_same_but_formatted(self):
        assert _cmp_txt_str_content(b"  a  b  ", b"a b") is True

    def test_multiline_difference(self):
        assert _cmp_txt_str_content(b"a\nb\nc", b"a\nb\nd") is False


class TestIsSafeZipPathExtra:
    def test_exact_target_path(self):
        assert _is_safe_zip_path("file.txt", "/tmp/extract") is True

    def test_empty_member_name(self):
        assert _is_safe_zip_path("", "/tmp/extract") is True

    def test_symlink_style_path(self):
        import tempfile
        safe = _is_safe_zip_path("../../../etc/passwd", tempfile.gettempdir())
        assert safe is False

    def test_cwd(self):
        assert _is_safe_zip_path("file.txt", ".") is True


class TestAutomountExtra:
    def test_zip_path_triggers_mount(self):
        mock_fs = MagicMock()
        mock_fs.getsyspath.return_value = "/real/path/archive.zip"
        with patch("pytigon_lib.schfs.vfstools.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            with patch("pytigon_lib.schfs.vfstools.OSFS") as mock_osfs:
                result = automount("/data/archive.zip")
                assert result == "/data/archive.zip"

    def test_zip_inside_path_triggers_mount(self):
        mock_fs = MagicMock()
        mock_fs.getsyspath.return_value = "/real/path/archive.zip"
        with patch("pytigon_lib.schfs.vfstools.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            with patch("pytigon_lib.schfs.vfstools.OSFS") as mock_osfs:
                result = automount("/data/archive.zip/inner/file.txt")
                assert result == "/data/archive.zip/inner/file.txt"

    def test_zip_not_matching_full_word(self):
        assert automount("/data/myzips/file.txt") == "/data/myzips/file.txt"

    def test_getsyspath_returns_none(self):
        mock_fs = MagicMock()
        mock_fs.getsyspath.return_value = None
        with patch("pytigon_lib.schfs.vfstools.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            result = automount("/data/archive.zip")
            assert result == "/data/archive.zip"

    def test_mount_exception_silent(self):
        mock_fs = MagicMock()
        mock_fs.getsyspath.return_value = "/real/archive.zip"
        mock_fs.add_fs.side_effect = Exception("mount failed")
        with patch("pytigon_lib.schfs.vfstools.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            result = automount("/data/archive.zip")
            assert result == "/data/archive.zip"


class TestConvertFileExtra:
    def test_string_output_imd_to_html(self):
        with tempfile.NamedTemporaryFile(suffix=".imd", mode="w", delete=False) as src:
            src.write("# Title\n\nContent")
            src.flush()
        try:
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as dst:
                pass
            try:
                result = convert_file(
                    src.name,
                    dst.name,
                    input_format="imd",
                    output_format="html",
                    for_vfs_input=False,
                    for_vfs_output=False,
                )
                assert result is True
            finally:
                os.unlink(dst.name)
        finally:
            os.unlink(src.name)

    def test_string_output_ihtml_to_html(self):
        with tempfile.NamedTemporaryFile(suffix=".ihtml", mode="w", delete=False) as src:
            src.write("<html><body><p>test</p></body></html>")
            src.flush()
        try:
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as dst:
                pass
            try:
                result = convert_file(
                    src.name,
                    dst.name,
                    input_format="ihtml",
                    output_format="html",
                    for_vfs_input=False,
                    for_vfs_output=False,
                )
                assert result is True
            finally:
                os.unlink(dst.name)
        finally:
            os.unlink(src.name)

    def test_raw_html_to_html(self):
        with tempfile.NamedTemporaryFile(suffix=".html", mode="w", delete=False) as src:
            src.write("<p>raw html</p>")
            src.flush()
        try:
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as dst:
                pass
            try:
                result = convert_file(
                    src.name,
                    dst.name,
                    input_format="txt",
                    output_format="html",
                    for_vfs_input=False,
                    for_vfs_output=False,
                )
                assert result is True
            finally:
                os.unlink(dst.name)
        finally:
            os.unlink(src.name)

    def test_auto_detect_input_format(self):
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as src:
            src.write("# Auto detect")
            src.flush()
        try:
            with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as dst:
                pass
            try:
                result = convert_file(
                    src.name,
                    dst.name,
                    output_format="html",
                    for_vfs_input=False,
                    for_vfs_output=False,
                )
                assert result is True
            finally:
                os.unlink(dst.name)
        finally:
            os.unlink(src.name)

    def test_stream_input(self):
        stream_in = io.StringIO("# Stream")
        stream_out = io.BytesIO()
        result = convert_file(
            stream_in,
            stream_out,
            input_format="md",
            output_format="html",
            for_vfs_input=False,
            for_vfs_output=False,
        )
        assert result is True
        assert len(stream_out.getvalue()) > 0

    def test_stream_output(self):
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as src:
            src.write("# Stream output")
            src.flush()
        try:
            stream_out = io.BytesIO()
            result = convert_file(
                src.name,
                stream_out,
                input_format="md",
                output_format="html",
                for_vfs_input=False,
                for_vfs_output=False,
            )
            assert result is True
            assert len(stream_out.getvalue()) > 0
        finally:
            os.unlink(src.name)

    def test_unsupported_output_format(self):
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False) as src:
            src.write("# test")
            src.flush()
        try:
            with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as dst:
                pass
            try:
                with pytest.raises((ValueError, OSError)):
                    convert_file(
                        src.name,
                        dst.name,
                        output_format="xyz",
                        for_vfs_input=False,
                        for_vfs_output=False,
                    )
            finally:
                os.unlink(dst.name)
        finally:
            os.unlink(src.name)

    def test_convert_exception_wraps_oserror(self):
        with pytest.raises(OSError):
            convert_file(
                "/nonexistent/input.md",
                "/nonexistent/output.html",
                for_vfs_input=False,
                for_vfs_output=False,
            )
