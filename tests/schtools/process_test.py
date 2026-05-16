from unittest.mock import patch

# Pytest tests
import pytest

from pytigon_lib.schtools.process import *


def test_run_success():
    with patch("subprocess.Popen") as mock_popen:
        mock_popen.return_value.communicate.return_value = (b"stdout", b"stderr")
        mock_popen.return_value.wait.return_value = 0

        exit_code, output, err = run(["ls", "-la"])
        assert exit_code == 0
        assert isinstance(output, list)
        assert err is None


if __name__ == "__main__":
    pytest.main()
