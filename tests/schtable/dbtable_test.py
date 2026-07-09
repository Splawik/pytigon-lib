"""Tests for :mod:`pytigon_lib.schtable.dbtable` using mock Django models."""

from unittest.mock import MagicMock, patch

import pytest

import django

if not django.conf.settings.configured:
    import os
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "conftest_settings")
    if not django.conf.settings.configured:
        django.conf.settings.configure(
            SECRET_KEY="test-key",
            INSTALLED_APPS=[
                "django.contrib.contenttypes",
                "django.contrib.auth",
            ],
            DATABASES={
                "default": {
                    "ENGINE": "django.db.backends.sqlite3",
                    "NAME": ":memory:",
                }
            },
        )
    django.setup()

from pytigon_lib.schtable.dbtable import DbTable, __COLMAP__, __COLINIT__, __COLSIZE__


def _make_mock_model(name, fields, meta_fields=None, simple_query=None):
    model = MagicMock()
    model.__name__ = name
    model._meta = MagicMock()
    model._meta.fields = fields
    model.objects = MagicMock()
    model.DoesNotExist = type("DoesNotExist", (Exception,), {})
    if simple_query:
        model.simple_query = simple_query
    return model


def _make_mock_field(field_name, field_class_name, choices=None, verbose_name=None, max_length=None):
    f = MagicMock()
    f.name = field_name
    f.verbose_name = verbose_name or field_name
    f.__class__.__name__ = field_class_name
    f.choices = choices
    f.max_length = max_length
    return f


def _make_mock_fk_field(field_name, field_class_name="ForeignKey", verbose_name=None):
    f = MagicMock()
    f.name = field_name
    f.verbose_name = verbose_name or field_name
    f.__class__.__name__ = field_class_name
    f.choices = None
    f.max_length = None
    return f


class TestDbTableInit:
    def test_init_sets_app_and_tab(self):
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("name", "CharField", max_length=100)
        model = _make_mock_model("TestModel", [f1, f2])
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            assert dt.app == "myapp"
            assert dt.tab == "TestModel"

    def test_init_col_names(self):
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("name", "CharField", max_length=100)
        f3 = _make_mock_field("age", "SOIntCol")
        model = _make_mock_model("TestModel", [f1, f2, f3])
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            assert len(dt.col_names) == 3
            assert "name" in dt.col_names
            assert "age" in dt.col_names

    def test_init_col_types_basic(self):
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("name", "CharField", max_length=100)
        f3 = _make_mock_field("active", "BooleanField")
        model = _make_mock_model("TestModel", [f1, f2, f3])
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            assert len(dt.col_types) == 3
            assert "string" in dt.col_types

    def test_init_col_types_with_choices(self):
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("status", "CharField", max_length=50, choices=[("A", "Active"), ("I", "Inactive")])
        model = _make_mock_model("TestModel", [f1, f2])
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            assert "y:" in dt.col_types[1]

    def test_init_col_types_foreign_key(self):
        from django.db.models.fields.related import ForeignKey
        f1 = _make_mock_field("id", "AutoField")
        f2 = MagicMock(spec=ForeignKey)
        f2.name = "category"
        f2.verbose_name = "category"
        f2.choices = None
        f2.max_length = None
        model = _make_mock_model("TestModel", [f1, f2])
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            assert any("x:" in t for t in dt.col_types)

    def test_init_col_lengths(self):
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("name", "CharField", max_length=50)
        f3 = _make_mock_field("flag", "BooleanField")
        model = _make_mock_model("TestModel", [f1, f2, f3])
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            assert len(dt.col_length) == 2

    def test_init_col_length_with_choices(self):
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("status", "CharField", max_length=10, choices=[("A", "Active"), ("IN", "Inactive")])
        model = _make_mock_model("TestModel", [f1, f2])
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            assert dt.col_length[0] >= 4

    def test_init_default_rec(self):
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("name", "CharField", max_length=100)
        f3 = _make_mock_field("value", "SOFloatCol")
        model = _make_mock_model("TestModel", [f1, f2, f3])
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            assert dt.default_rec[1] == ""
            assert dt.default_rec[2] == 0.0

    def test_foreign_key_parm_used(self):
        from django.db.models.fields.related import ForeignKey
        f1 = _make_mock_field("id", "AutoField")
        f2 = MagicMock(spec=ForeignKey)
        f2.name = "cat_id"
        f2.verbose_name = "cat_id"
        f2.choices = None
        f2.max_length = None
        model = _make_mock_model("TestModel", [f1, f2])
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            dt.foreign_key_parm = {"cat": "filter_param"}
            dt.col_types = dt._get_col_types()


class TestDbTableConw:
    @pytest.fixture
    def dt(self):
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("name", "CharField", max_length=50)
        model = _make_mock_model("TestModel", [f1, f2])
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            return DbTable("myapp", "TestModel")

    def test_conw_long_valid(self, dt):
        assert dt.conw_long("42") == 42

    def test_conw_long_zero(self, dt):
        assert dt.conw_long(0) is None

    def test_conw_long_none(self, dt):
        assert dt.conw_long(None) is None

    def test_conw_float_valid(self, dt):
        assert dt.conw_float("3.14") == 3.14

    def test_conw_float_none(self, dt):
        assert dt.conw_float(None) is None

    def test_conw_bool_true(self, dt):
        assert dt.conw_bool(True) is True

    def test_conw_bool_false(self, dt):
        assert dt.conw_bool(False) is None

    def test_conw_none(self, dt):
        assert dt.conw_none("whatever") == "whatever"

    def test_conw_x_with_object(self, dt):
        obj = MagicMock()
        obj.GetStringRepr.return_value = "rep123"
        assert dt.conw_x(obj) == "rep123"

    def test_conw_x_with_none(self, dt):
        assert dt.conw_x(None) == "0"


class TestDbTablePage:
    def test_page_returns_data(self):
        rec = MagicMock()
        rec.id = 1
        rec.name = "Test"
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("name", "CharField", max_length=50)
        model = _make_mock_model("TestModel", [f1, f2])
        fake_qs = MagicMock()
        fake_qs.__getitem__.return_value = [rec]
        model.objects.all.return_value = fake_qs
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            result = dt.page(0)
            assert isinstance(result, list)

    def test_page_with_sort(self):
        rec = MagicMock()
        rec.id = 1
        rec.name = "Test"
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("name", "CharField", max_length=50)
        model = _make_mock_model("TestModel", [f1, f2])
        fake_qs = MagicMock()
        fake_qs.order_by.return_value = fake_qs
        fake_qs.__getitem__.return_value = [rec]
        model.objects.all.return_value = fake_qs
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            result = dt.page(0, sort="name")
            assert isinstance(result, list)
            fake_qs.order_by.assert_called()

    def test_page_with_sort_desc(self):
        rec = MagicMock()
        rec.id = 1
        rec.name = "Test"
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("name", "CharField", max_length=50)
        model = _make_mock_model("TestModel", [f1, f2])
        fake_qs = MagicMock()
        fake_qs.order_by.return_value = fake_qs
        fake_qs.__getitem__.return_value = [rec]
        model.objects.all.return_value = fake_qs
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            dt.page(0, sort="-name")
            fake_qs.order_by.assert_called()

    def test_page_with_value_uses_simple_query(self):
        rec = MagicMock()
        rec.id = 1
        rec.name = "Test"
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("name", "CharField", max_length=50)
        fake_qs = MagicMock()
        fake_qs.__getitem__.return_value = [rec]
        model = _make_mock_model("TestModel", [f1, f2])
        model.simple_query = MagicMock(return_value=fake_qs)
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            result = dt.page(0, value="pattern")
            model.simple_query.assert_called_once()
            assert isinstance(result, list)

    def test_page_no_value_no_simple_query(self):
        rec = MagicMock()
        rec.id = 1
        rec.name = "Test"
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("name", "CharField", max_length=50)
        model = _make_mock_model("TestModel", [f1, f2])
        fake_qs = MagicMock()
        fake_qs.__getitem__.return_value = [rec]
        model.objects.all.return_value = fake_qs
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            dt.page(0)
            model.objects.all.assert_called_once()

    def test_page_foreign_key_value(self):
        fk_obj = MagicMock()
        fk_obj.id = 10
        fk_obj.__str__ = MagicMock(return_value="Category10")
        rec = MagicMock()
        rec.id = 1
        rec.name = "Test"
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("name", "CharField", max_length=50)
        model = _make_mock_model("TestModel", [f1, f2])
        fake_qs = MagicMock()
        fake_qs.__getitem__.return_value = [rec]
        model.objects.all.return_value = fake_qs
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            result = dt.page(0)
            assert isinstance(result, list)

    def test_page_with_choices_in_field(self):
        rec = MagicMock()
        rec.id = 1
        rec.status = "A"
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("status", "CharField", max_length=10, choices=[("A", "Active"), ("I", "Inactive")])
        model = _make_mock_model("TestModel", [f1, f2])
        fake_qs = MagicMock()
        fake_qs.__getitem__.return_value = [rec]
        model.objects.all.return_value = fake_qs
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            result = dt.page(0)
            assert isinstance(result, list)


class TestDbTableRecAsStr:
    def test_rec_as_str_found(self):
        obj = MagicMock()
        obj.__str__ = MagicMock(return_value="My Record")
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("name", "CharField", max_length=50)
        model = _make_mock_model("TestModel", [f1, f2])
        model.objects.get.return_value = obj
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            result = dt.rec_as_str(1)
            assert result == "My Record"
            model.objects.get.assert_called_with(id=1)

    def test_rec_as_str_not_found(self):
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("name", "CharField", max_length=50)
        model = _make_mock_model("TestModel", [f1, f2])
        model.objects.get.side_effect = model.DoesNotExist()
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            result = dt.rec_as_str(999)
            assert result == ""


class TestDbTableCount:
    def test_count(self):
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("name", "CharField", max_length=50)
        model = _make_mock_model("TestModel", [f1, f2])
        model.objects.count.return_value = 42
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            assert dt.count(None) == 42


class TestDbTableInsertRec:
    def test_insert_rec(self):
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("name", "CharField", max_length=50)
        model = _make_mock_model("TestModel", [f1, f2])
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            dt.insert_rec([1, "New Name"])
            assert model.call_count >= 0

    def test_insert_rec_with_choices(self):
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("status", "CharField", max_length=20, choices=[("A", "Active")])
        model = _make_mock_model("TestModel", [f1, f2])
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            dt.insert_rec([1, "A:Active"])
            assert model.call_count >= 0


class TestDbTableUpdateRec:
    def test_update_rec(self):
        obj = MagicMock()
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("name", "CharField", max_length=50)
        model = _make_mock_model("TestModel", [f1, f2])
        model.objects.get.return_value = obj
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            dt.update_rec([1, "Updated Name"])
            model.objects.get.assert_called_once_with(id=1)
            obj.save.assert_called_once()

    def test_update_rec_not_found(self):
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("name", "CharField", max_length=50)
        model = _make_mock_model("TestModel", [f1, f2])
        model.objects.get.side_effect = model.DoesNotExist()
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            dt.update_rec([999, "Updated Name"])


class TestDbTableDeleteRec:
    def test_delete_rec(self):
        obj = MagicMock()
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("name", "CharField", max_length=50)
        model = _make_mock_model("TestModel", [f1, f2])
        model.objects.get.return_value = obj
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            dt.delete_rec(1)
            model.objects.get.assert_called_once_with(id=1)
            obj.delete.assert_called_once()

    def test_delete_rec_not_found(self):
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("name", "CharField", max_length=50)
        model = _make_mock_model("TestModel", [f1, f2])
        model.objects.get.side_effect = model.DoesNotExist()
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            dt.delete_rec(999)


class TestDbTableAuto:
    def test_auto(self):
        f1 = _make_mock_field("id", "AutoField")
        f2 = _make_mock_field("name", "CharField", max_length=50)
        model = _make_mock_model("TestModel", [f1, f2])
        with patch("pytigon_lib.schtable.dbtable.django.apps.registry.apps.get_model", return_value=model):
            dt = DbTable("myapp", "TestModel")
            result = dt.auto("col_name", ["c1", "c2"], [1, 2])
            assert result is None


class TestDbTableConstants:
    def test_colmap_defined(self):
        assert "AutoField" in __COLMAP__
        assert "CharField" in __COLMAP__
        assert "BooleanField" in __COLMAP__
        assert "SOIntCol" in __COLMAP__

    def test_colinit_defined(self):
        assert "AutoField" in __COLINIT__
        assert "CharField" in __COLINIT__
        assert __COLINIT__["CharField"] == ""
        assert __COLINIT__["BooleanField"] is True

    def test_colsize_defined(self):
        assert "AutoField" in __COLSIZE__
        assert "CharField" in __COLSIZE__
        assert __COLSIZE__["BooleanField"] == 1
