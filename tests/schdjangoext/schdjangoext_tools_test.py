from pytigon_lib.schdjangoext.tools import *

# Pytest tests
import pytest


def test_import_model():
    """Test the import_model function."""
    # Mocking Django settings and sys.modules for testing is complex, so this is a placeholder.
    # In a real test environment, you would mock these dependencies.
    assert import_model("nonexistent_app", "nonexistent_model") is None


def test_gettempdir(settings):
    """Test the gettempdir function."""
    settings.TEMP_PATH = "/tmp"
    assert gettempdir() == "/tmp"


def test_make_href(settings):
    """Test the make_href function."""
    settings.URL_ROOT_FOLDER = "root"
    assert make_href("/path") == "/root/path"
    assert make_href("/path", "base?param=1") == "/root/path?param=1"


def test_from_migrations():
    """Test the from_migrations function."""
    sys.argv = ["manage.py", "makemigrations"]
    assert from_migrations() is True
    sys.argv = ["manage.py", "runserver"]
    assert from_migrations() is False
