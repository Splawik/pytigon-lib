from pytigon_lib.schtools.env import *

# Pytest tests
import pytest


def test_get_environ_no_path():
    """Test get_environ with no path provided."""
    env = get_environ()
    assert env is not None
    assert isinstance(env, environ.Env)


if __name__ == "__main__":
    pytest.main()
