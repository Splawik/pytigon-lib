from pytigon_lib.schfs import *

# Pytest tests
import pytest
from unittest.mock import patch


def test_get_vfs_success():
    """Test successful retrieval of the default VFS."""
    with patch("django.core.files.storage.default_storage.fs", "mock_vfs"):
        assert get_vfs() == "mock_vfs"


if __name__ == "__main__":
    pytest.main()
