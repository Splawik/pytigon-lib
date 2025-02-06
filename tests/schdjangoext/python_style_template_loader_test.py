from pytigon_lib.schdjangoext.python_style_template_loader import *

# Pytest tests
import pytest
from unittest.mock import patch, mock_open
from django.template.engine import Engine
from django.template import Origin


@pytest.fixture
def mock_settings():
    return {
        "TEMPLATES": [{"DIRS": ["/templates"]}],
        "LANGUAGES": [("en", "English"), ("pl", "Polish")],
        "PRJ_PATH": "/project",
        "PRJ_PATH_ALT": "/alt_project",
        "DATA_PATH": "/data",
    }


def test_compile_template(mock_settings):
    with patch.dict("django.conf.settings.__dict__", mock_settings):
        with patch("os.path.exists", return_value=True):
            with patch("os.makedirs"):
                with patch("os.path.getmtime", side_effect=[100, 200]):
                    with patch("codecs.open", mock_open()) as mock_file:
                        compile_template("test.ihtml", force=True)
                        mock_file.assert_called()


def test_fs_loader_get_template_sources():
    engine = Engine()
    loader = FSLoader(engine)
    with patch.object(loader, "get_dirs", return_value=["/templates"]):
        sources = list(loader.get_template_sources("test.html"))
        assert len(sources) > 0
