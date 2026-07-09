from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schfs.tasks import filesystemcmd


class TestFilesystemcmdDelete:
    def test_remove_file(self):
        mock_fs = MagicMock()
        mock_fs.isfile.return_value = True
        with patch("pytigon_lib.schfs.tasks.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            filesystemcmd(param={"cmd": "DELETE", "files": ["/tmp/file.txt"]})
        mock_fs.remove.assert_called_once_with("/tmp/file.txt")

    def test_remove_directory(self):
        mock_fs = MagicMock()
        mock_fs.isfile.return_value = False
        with patch("pytigon_lib.schfs.tasks.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            filesystemcmd(param={"cmd": "DELETE", "files": ["/tmp/mydir"]})
        mock_fs.removetree.assert_called_once_with("/tmp/mydir")

    def test_delete_multiple_files(self):
        mock_fs = MagicMock()
        mock_fs.isfile.return_value = True
        with patch("pytigon_lib.schfs.tasks.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            filesystemcmd(param={"cmd": "DELETE", "files": ["/a.txt", "/b.txt"]})
        assert mock_fs.remove.call_count == 2

    def test_delete_ignores_errors(self):
        mock_fs = MagicMock()
        mock_fs.isfile.side_effect = OSError("boom")
        with patch("pytigon_lib.schfs.tasks.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            filesystemcmd(param={"cmd": "DELETE", "files": ["/bad.txt"]})
        assert mock_fs.isfile.called


class TestFilesystemcmdCopy:
    def test_copy_file(self):
        mock_fs = MagicMock()
        mock_fs.isfile.return_value = True
        with patch("pytigon_lib.schfs.tasks.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            filesystemcmd(param={"cmd": "COPY", "files": ["/src/file.txt"], "dest": "/dst"})
        mock_fs.copy.assert_called_once_with("/src/file.txt", "/dst/file.txt", overwrite=True)

    def test_copy_directory(self):
        mock_fs = MagicMock()
        mock_fs.isfile.return_value = False
        with patch("pytigon_lib.schfs.tasks.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            filesystemcmd(param={"cmd": "COPY", "files": ["/src/mydir"], "dest": "/dst"})
        mock_fs.copydir.assert_called_once_with(
            "/src/mydir", "/dst/mydir", overwrite=True, ignore_errors=True
        )

    def test_copy_with_trailing_slash_dest(self):
        mock_fs = MagicMock()
        mock_fs.isfile.return_value = True
        with patch("pytigon_lib.schfs.tasks.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            filesystemcmd(param={"cmd": "COPY", "files": ["/src/f.txt"], "dest": "/dst/"})
        mock_fs.copy.assert_called_once_with("/src/f.txt", "/dst/f.txt", overwrite=True)

    def test_copy_multiple_files(self):
        mock_fs = MagicMock()
        mock_fs.isfile.return_value = True
        with patch("pytigon_lib.schfs.tasks.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            filesystemcmd(param={"cmd": "COPY", "files": ["/a.txt", "/b.txt"], "dest": "/out"})
        assert mock_fs.copy.call_count == 2

    def test_copy_ignores_errors(self):
        mock_fs = MagicMock()
        mock_fs.isfile.side_effect = OSError("boom")
        with patch("pytigon_lib.schfs.tasks.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            filesystemcmd(param={"cmd": "COPY", "files": ["/bad.txt"], "dest": "/out"})


class TestFilesystemcmdMove:
    def test_move_file(self):
        mock_fs = MagicMock()
        mock_fs.isfile.return_value = True
        with patch("pytigon_lib.schfs.tasks.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            filesystemcmd(param={"cmd": "MOVE", "files": ["/src/file.txt"], "dest": "/dst"})
        mock_fs.move.assert_called_once_with("/src/file.txt", "/dst/file.txt", overwrite=True)

    def test_move_directory(self):
        mock_fs = MagicMock()
        mock_fs.isfile.return_value = False
        with patch("pytigon_lib.schfs.tasks.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            filesystemcmd(param={"cmd": "MOVE", "files": ["/src/mydir"], "dest": "/dst"})
        mock_fs.movedir.assert_called_once_with(
            "/src/mydir", "/dst/mydir", overwrite=True, ignore_errors=True
        )


class TestFilesystemcmdCproxy:
    def test_sends_start_and_stop_events(self):
        cproxy = MagicMock()
        with patch("pytigon_lib.schfs.tasks.default_storage") as mock_storage:
            mock_fs = MagicMock()
            mock_fs.isfile.return_value = True
            mock_storage.fs = mock_fs
            filesystemcmd(cproxy=cproxy, param={"cmd": "DELETE", "files": ["/f.txt"]})
        cproxy.send_event.assert_any_call("start")
        cproxy.send_event.assert_any_call("stop")

    def test_sends_stop_on_error(self):
        cproxy = MagicMock()
        with patch("pytigon_lib.schfs.tasks.default_storage") as mock_storage:
            mock_fs = MagicMock()
            mock_fs.isfile.side_effect = RuntimeError("fail")
            mock_storage.fs = mock_fs
            filesystemcmd(cproxy=cproxy, param={"cmd": "DELETE", "files": ["/f.txt"]})
        cproxy.send_event.assert_any_call("start")
        cproxy.send_event.assert_any_call("stop")


class TestFilesystemcmdValidation:
    def test_invalid_cmd(self):
        with pytest.raises(ValueError):
            filesystemcmd(param={"cmd": "INVALID", "files": ["file.txt"]})

    def test_missing_params_empty_dict(self):
        with pytest.raises(ValueError):
            filesystemcmd(param={})

    def test_missing_param_key(self):
        with pytest.raises(ValueError):
            filesystemcmd()

    def test_empty_files_list(self):
        with pytest.raises(ValueError):
            filesystemcmd(param={"cmd": "DELETE", "files": []})

    def test_empty_cmd_string(self):
        with pytest.raises(ValueError):
            filesystemcmd(param={"cmd": "", "files": ["f.txt"]})
