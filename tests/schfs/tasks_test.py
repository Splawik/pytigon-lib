from pytigon_lib.schfs.tasks import *

# Pytest tests
import pytest
from unittest.mock import MagicMock


def test_filesystemcmd_delete():
    param = {"cmd": "DELETE", "files": ["file1.txt", "dir1"]}
    filesystemcmd(None, param=param)


def test_filesystemcmd_copy():
    param = {"cmd": "COPY", "files": ["file1.txt"], "dest": "backup"}
    filesystemcmd(None, param=param)


def test_filesystemcmd_move():
    param = {"cmd": "MOVE", "files": ["file1.txt"], "dest": "backup"}
    filesystemcmd(None, param=param)


def test_filesystemcmd_invalid_cmd():
    param = {"cmd": "INVALID", "files": ["file1.txt"]}
    with pytest.raises(ValueError):
        filesystemcmd(None, param=param)


def test_filesystemcmd_missing_params():
    with pytest.raises(ValueError):
        filesystemcmd(None, param={})


if __name__ == "__main__":
    pytest.main()
