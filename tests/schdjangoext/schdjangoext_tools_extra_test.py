from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schdjangoext.tools import from_migrations, gettempdir, import_model, make_href

import sys


class TestImportModelExtra:
    def test_import_model_module_already_cached(self):
        fake_module = MagicMock()
        fake_module.models = MagicMock()
        fake_model_class = MagicMock()
        fake_module.models.MyModel = fake_model_class
        with patch.dict("sys.modules", {"myapp.models": fake_module}, clear=False):
            result = import_model("myapp", "MyModel")
            assert result is fake_model_class

    def test_import_model_fresh_import(self):
        expected = MagicMock()
        fake_module = MagicMock()
        fake_module.SomeModel = expected
        fake_module.models = fake_module
        with patch("builtins.__import__", return_value=fake_module) as mock_import:
            result = import_model("myapp2", "SomeModel")
            assert mock_import.called
            assert result is expected

    def test_import_model_attribute_error_returns_none(self):
        with patch("builtins.__import__", side_effect=AttributeError):
            with patch("traceback.print_exc"):
                result = import_model("bad", "Model")
                assert result is None


class TestMakeHrefExtra:
    def test_make_href_with_url_root_folder(self):
        from django.conf import settings as s
        s.URL_ROOT_FOLDER = "root"
        try:
            result = make_href("/path/to/resource")
            assert result == "/root/path/to/resource"
        finally:
            del s.URL_ROOT_FOLDER

    def test_make_href_no_root_folder(self):
        from django.conf import settings as s
        s.URL_ROOT_FOLDER = ""
        try:
            result = make_href("/path/to/resource")
            assert result == "/path/to/resource"
        finally:
            del s.URL_ROOT_FOLDER

    def test_make_href_already_has_query(self):
        from django.conf import settings as s
        s.URL_ROOT_FOLDER = ""
        try:
            result = make_href("/path?existing=1", "base?new=2")
            assert "existing=1" in result
            assert "new=2" in result
        finally:
            del s.URL_ROOT_FOLDER

    def test_make_href_base_without_question(self):
        from django.conf import settings as s
        s.URL_ROOT_FOLDER = ""
        try:
            result = make_href("/path", "base_no_query")
            assert result == "/path"
        finally:
            del s.URL_ROOT_FOLDER

    def test_make_href_no_base_url(self):
        from django.conf import settings as s
        s.URL_ROOT_FOLDER = ""
        try:
            result = make_href("/path", None)
            assert result == "/path"
        finally:
            del s.URL_ROOT_FOLDER

    def test_make_href_relative_path_no_root(self):
        from django.conf import settings as s
        s.URL_ROOT_FOLDER = ""
        try:
            result = make_href("relative/path")
            assert result == "relative/path"
        finally:
            del s.URL_ROOT_FOLDER


class TestFromMigrationsExtra:
    def test_from_migrations_exporttolocaldb(self):
        sys.argv = ["manage.py", "exporttolocaldb"]
        assert from_migrations() is True
        sys.argv = ["manage.py", "runserver"]

    def test_from_migrations_makeallmigrations(self):
        sys.argv = ["manage.py", "makeallmigrations"]
        assert from_migrations() is True
        sys.argv = ["manage.py", "runserver"]

    def test_from_migrations_not_in_subcommand(self):
        sys.argv = ["manage.py", "shell"]
        assert from_migrations() is False
        sys.argv = ["manage.py", "runserver"]


class TestGetTempDirExtra:
    def test_gettempdir_custom_path(self):
        from django.conf import settings as s
        s.TEMP_PATH = "/var/tmp/custom"
        try:
            assert gettempdir() == "/var/tmp/custom"
        finally:
            del s.TEMP_PATH
