from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from pytigon_lib.schfs import get_vfs, open_file, get_temp_filename, get_unique_filename, open_and_create_dir


class TestGetVfs:
    def test_returns_fs_from_default_storage(self):
        mock_fs = MagicMock()
        with patch("pytigon_lib.schfs.default_storage") as mock_storage:
            type(mock_storage).fs = PropertyMock(return_value=mock_fs)
            result = get_vfs()
        assert result is mock_fs

    def test_raises_runtime_error_when_no_fs(self):
        with patch("pytigon_lib.schfs.default_storage") as mock_storage:
            del mock_storage.fs
            with pytest.raises(RuntimeError, match="default VFS"):
                get_vfs()


class TestOpenFile:
    def test_opens_local_file(self):
        mock_open = MagicMock()
        with patch("pytigon_lib.schfs.vfstools.open", mock_open):
            with patch("pytigon_lib.schfs.vfstools.default_storage"):
                open_file("/tmp/test.txt", "r", for_vfs=False)
            mock_open.assert_called_once_with("/tmp/test.txt", "r")

    def test_opens_vfs_file(self):
        mock_fs = MagicMock()
        with patch("pytigon_lib.schfs.vfstools.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            open_file("/vfs/test.txt", "w", for_vfs=True)
            mock_fs.open.assert_called_once_with("/vfs/test.txt", "w")


class TestGetTempFilename:
    def test_returns_path(self):
        filename = get_temp_filename("base", "txt")
        assert isinstance(filename, str)
        assert "base" in filename


class TestGetUniqueFilename:
    def test_returns_string(self):
        filename = get_unique_filename()
        assert isinstance(filename, str)
        assert len(filename) > 0

    def test_includes_base(self):
        filename = get_unique_filename("myreport")
        assert "myreport" in filename


class TestOpenAndCreateDir:
    def test_creates_dir_locally(self):
        mock_open_file = MagicMock()
        mock_os_path_exists = MagicMock(return_value=False)
        mock_os_makedirs = MagicMock()
        with patch("pytigon_lib.schfs.vfstools.open_file", mock_open_file):
            with patch("os.path.exists", mock_os_path_exists):
                with patch("os.makedirs", mock_os_makedirs):
                    open_and_create_dir("/tmp/sub/test.txt", "w", for_vfs=False)
        mock_os_makedirs.assert_called_once_with("/tmp/sub")

    def test_creates_dir_for_vfs(self):
        mock_open_file = MagicMock()
        mock_fs = MagicMock()
        mock_fs.exists.return_value = False
        with patch("pytigon_lib.schfs.vfstools.open_file", mock_open_file):
            with patch("pytigon_lib.schfs.vfstools.default_storage") as mock_storage:
                mock_storage.fs = mock_fs
                open_and_create_dir("/vfs/sub/test.txt", "w", for_vfs=True)
        mock_fs.makedirs.assert_called_once_with("/vfs/sub")

    def test_skips_mkdir_when_exists(self):
        mock_open_file = MagicMock()
        with patch("pytigon_lib.schfs.vfstools.open_file", mock_open_file):
            with patch("os.path.exists", return_value=True):
                with patch("os.makedirs") as mock_makedirs:
                    open_and_create_dir("/existing/test.txt", "w", for_vfs=False)
        mock_makedirs.assert_not_called()

    def test_vfs_skips_makedirs_when_exists(self):
        mock_open_file = MagicMock()
        mock_fs = MagicMock()
        mock_fs.exists.return_value = True
        with patch("pytigon_lib.schfs.vfstools.open_file", mock_open_file):
            with patch("pytigon_lib.schfs.vfstools.default_storage") as mock_storage:
                mock_storage.fs = mock_fs
                open_and_create_dir("/vfs/existing/test.txt", "w", for_vfs=True)
        mock_fs.makedirs.assert_not_called()


class TestImportExtractall:
    def test_extractall_is_importable(self):
        from pytigon_lib.schfs import extractall as mod_extractall
        from pytigon_lib.schfs.vfstools import extractall as vfs_extractall

        assert mod_extractall is vfs_extractall
