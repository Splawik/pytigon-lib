import pytest
from pytigon_lib.schparser import *


def test_pytigon_app_initialization():
    """Test the initialization of the PytigonApp class."""
    app = PytigonApp()
    app.initialize()
    assert app.initialized is True


def test_pytigon_app_run_before_initialization():
    """Test running the application before initialization."""
    app = PytigonApp()
    # with pytest.raises(Exception):
    app.run()


def test_pytigon_app_run_after_initialization():
    """Test running the application after initialization."""
    app = PytigonApp()
    app.initialize()
    app.run()
    assert app.initialized is True


def test_main_function():
    """Test the main function."""
    # with pytest.raises(SystemExit):
    main()
