from pytigon_lib.schtools.process import *

# Pytest tests
import pytest
from unittest.mock import patch, MagicMock


def test_run_success():
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value.communicate.return_value = (b"stdout", b"stderr")
        mock_popen.return_value.wait.return_value = 0

        exit_code, output, err = run(["ls", "-la"])
        assert exit_code == 0
        assert type(output) == list
        assert err == None


if __name__ == "__main__":
    pytest.main()
