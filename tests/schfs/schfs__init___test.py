from unittest.mock import patch

# Pytest tests
import pytest

from pytigon_lib.schfs import *


def test_get_vfs_success():
    """Test successful retrieval of the default VFS."""
    with patch("django.core.files.storage.default_storage.fs", "mock_vfs"):
        assert get_vfs() == "mock_vfs"


if __name__ == "__main__":
    pytest.main()
