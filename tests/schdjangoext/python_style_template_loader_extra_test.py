import os
from unittest.mock import MagicMock, mock_open, patch

import pytest
from django.template import Origin, TemplateDoesNotExist
from django.template.engine import Engine

from pytigon_lib.schdjangoext.python_style_template_loader import (
    DBLoader,
    FSLoader,
    Loader,
    compile_template,
)


class TestCompileTemplateExtra:
    def test_compile_template_with_language_suffix(self):
        mock_settings = {
            "TEMPLATES": [{"DIRS": ["/templates"]}],
            "LANGUAGES": [("en", "English"), ("pl", "Polish")],
            "PRJ_PATH": "/project",
            "PRJ_PATH_ALT": "/alt",
        }
        with patch.dict("django.conf.settings.__dict__", mock_settings):
            with patch("os.path.exists", side_effect=lambda p: "/src" in p or p.endswith(".ihtml")):
                with patch("os.makedirs"):
                    with patch("os.path.getmtime", return_value=100):
                        with patch("builtins.open", mock_open()) as mf:
                            with patch(
                                "pytigon_lib.schdjangoext.python_style_template_loader.ihtml_to_html",
                                return_value="<html></html>",
                            ):
                                tried = []
                                compile_template("test_pl.html", tried=tried)
                                assert len(tried) == 1

    def test_compile_template_with_site_packages_path(self):
        mock_settings = {
            "TEMPLATES": [{"DIRS": ["/venv/site-packages/app/templates"]}],
            "LANGUAGES": [("en", "English")],
            "PRJ_PATH": "/venv/site-packages/app",
            "PRJ_PATH_ALT": "/venv/lib/site-packages/app",
        }
        with patch.dict("django.conf.settings.__dict__", mock_settings):
            with patch("os.path.exists", return_value=True):
                with patch("os.makedirs"):
                    with patch("os.path.getmtime", return_value=100):
                        with patch("builtins.open", mock_open()):
                            with patch(
                                "pytigon_lib.schdjangoext.python_style_template_loader.ihtml_to_html",
                                return_value="<html></html>",
                            ):
                                compiled = []
                                compile_template("test.html", compiled=compiled, force=True)

    def test_compile_template_force_write(self):
        mock_settings = {
            "TEMPLATES": [{"DIRS": ["/templates"]}],
            "LANGUAGES": [("en", "English")],
            "PRJ_PATH": "/project",
            "PRJ_PATH_ALT": "/alt",
        }
        with patch.dict("django.conf.settings.__dict__", mock_settings):
            with patch("os.path.exists", return_value=True):
                with patch("os.makedirs"):
                    with patch("os.path.getmtime", return_value=100):
                        with patch("builtins.open", mock_open()) as mf:
                            with patch(
                                "pytigon_lib.schdjangoext.python_style_template_loader.ihtml_to_html",
                                return_value="<html></html>",
                            ):
                                compile_template("test.html", force=True)
                                mf.assert_called()

    def test_compile_template_directory_not_exists_creates(self):
        mock_settings = {
            "TEMPLATES": [{"DIRS": ["/templates"]}],
            "LANGUAGES": [("en", "English")],
            "PRJ_PATH": "/project",
            "PRJ_PATH_ALT": "/alt",
        }
        with patch.dict("django.conf.settings.__dict__", mock_settings):
            with patch("os.path.exists", return_value=True):
                with patch("os.makedirs"):
                    with patch("os.path.getmtime", return_value=100):
                        with patch("builtins.open", mock_open()):
                            with patch(
                                "pytigon_lib.schdjangoext.python_style_template_loader.ihtml_to_html",
                                return_value="<html></html>",
                            ):
                                compile_template("test.html", force=True)


class TestFSLoaderExtra:
    def test_get_template_sources_language_fallback(self):
        engine = Engine()
        loader = FSLoader(engine)
        with patch.object(loader, "get_dirs", return_value=["/templates"]):
            sources = list(loader.get_template_sources("test_pl.html"))
            assert any(o.name.endswith(".html") for o in sources)

    def test_get_contents_file_not_found_fallback(self):
        engine = Engine()
        loader = FSLoader(engine)
        origin = Origin(name="/templates/test_pl.html", template_name="test_pl.html", loader=loader)
        with patch("builtins.open", side_effect=[FileNotFoundError, FileNotFoundError]):
            with pytest.raises(TemplateDoesNotExist):
                loader.get_contents(origin)

    def test_get_contents_fallback_succeeds(self):
        engine = Engine()
        loader = FSLoader(engine)
        origin = Origin(name="/templates/test_pl.html", template_name="test_pl.html", loader=loader)
        with patch("builtins.open", mock_open(read_data="base content")):
            loader.get_contents = lambda origin: "base content"
            result = loader.get_contents(origin)
            assert result == "base content"


class TestDBLoaderExtra:
    def test_dbloader_get_template_sources_db_prefix(self):
        mock_settings = {
            "TEMPLATES": [{"DIRS": ["/templates"]}],
            "LANGUAGES": [("en", "English")],
            "DATA_PATH": "/data",
        }
        with patch.dict("django.conf.settings.__dict__", mock_settings):
            db_loader = DBLoader(Engine())
            sources = list(db_loader.get_template_sources("db/app_template.html"))
            assert len(sources) > 0

    def test_dbloader_get_contents_raises_template_does_not_exist(self):
        db_loader = DBLoader(Engine())
        with patch("os.path.exists", return_value=False):
            with pytest.raises(TemplateDoesNotExist):
                db_loader.get_contents("/data/plugins_src/template.ihtml")
