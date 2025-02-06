from pytigon_lib.schtable import *

# Pytest tests
import pytest


def test_pytigon_app_initialization():
    """Test the initialization of the PytigonApp class."""
    app = PytigonApp("TestApp")
    app.initialize()
    assert app._initialized is True


def test_pytigon_app_run():
    """Test the run method of the PytigonApp class."""
    app = PytigonApp("TestApp")
    app.initialize()
    app.run()
    # No assertion needed as the test checks for exceptions


if __name__ == "__main__":
    pytest.main()
