"""Tests for the optional PyArrow streaming export/import helpers.

The tests use lightweight fakes for Django models/querysets so that the module
can be exercised without a database. Both the PyArrow path and the standard
library fallback are covered.
"""

import csv
from datetime import date, datetime
from decimal import Decimal

import pytest

from pytigon_lib.schdjangoext import arrow_tools


class FakeField:
    def __init__(self, name, internal, target_field=None, max_digits=None, decimal_places=None):
        self.name = name
        self.attname = name
        self.internal = internal
        self.target_field = target_field
        self.max_digits = max_digits
        self.decimal_places = decimal_places
        self.choices = None

    def get_internal_type(self):
        return self.internal


class FakeMeta:
    def __init__(self, fields):
        self.fields = fields


class FakeManager:
    def __init__(self):
        self.created = []

    def bulk_create(self, objs, batch_size=None):
        self.created.extend(objs)


class FakeModel:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


def build_model():
    model = FakeModel
    model._meta = FakeMeta(
        [
            FakeField("id", "AutoField"),
            FakeField("name", "CharField"),
            FakeField("active", "BooleanField"),
            FakeField("score", "FloatField"),
            FakeField("created", "DateTimeField"),
            FakeField("day", "DateField"),
            FakeField("price", "DecimalField", max_digits=10, decimal_places=2),
            FakeField("meta", "JSONField"),
        ]
    )
    model._default_manager = FakeManager()
    model.objects = model._default_manager
    return model


def build_rows():
    return [
        (
            1,
            "alpha",
            True,
            1.5,
            datetime(2026, 1, 2, 3, 4, 5),
            date(2026, 1, 2),
            Decimal("9.99"),
            {"k": 1},
        ),
        (
            2,
            "beta",
            False,
            2.5,
            datetime(2026, 2, 3, 4, 5, 6),
            date(2026, 2, 3),
            Decimal("19.95"),
            {"k": 2},
        ),
    ]


class FakeValuesList:
    def __init__(self, rows):
        self._rows = rows

    def iterator(self, chunk_size=10000):
        return iter(self._rows)


class FakeQuerySet:
    def __init__(self, model, rows):
        self.model = model
        self._rows = rows

    def values_list(self, *names):
        return FakeValuesList(self._rows)


FIELDS = [
    "id",
    "name",
    "active",
    "score",
    "created",
    "day",
    "price",
    "meta",
]


def make_queryset():
    return FakeQuerySet(build_model(), build_rows())


def disable_arrow(monkeypatch):
    monkeypatch.setattr(arrow_tools, "_PYARROW", None)
    monkeypatch.setattr(arrow_tools, "_PYARROW_CHECKED", True)


class TestFieldMapping:
    def test_schema_types(self):
        pytest.importorskip("pyarrow")
        model = build_model()
        schema = arrow_tools.model_arrow_schema(model)
        pa = arrow_tools.pyarrow_module()
        assert schema.field("id").type == pa.int64()
        assert schema.field("name").type == pa.string()
        assert schema.field("active").type == pa.bool_()
        assert schema.field("score").type == pa.float64()
        assert schema.field("created").type == pa.timestamp("us")
        assert schema.field("day").type == pa.date32()
        assert schema.field("price").type == pa.decimal128(10, 2)
        assert schema.field("meta").type == pa.string()

    def test_format_from_name(self):
        assert arrow_tools.format_from_name("x.parquet") == "parquet"
        assert arrow_tools.format_from_name("x.feather") == "arrow"
        assert arrow_tools.format_from_name("x.csv") == "csv"
        assert arrow_tools.format_from_name("x.dat") is None


class TestQuerysetToArrow:
    def test_values_and_types(self):
        pa = pytest.importorskip("pyarrow")
        table = arrow_tools.queryset_to_arrow(make_queryset(), fields=FIELDS)
        assert table.num_rows == 2
        assert table.column("name").to_pylist() == ["alpha", "beta"]
        assert table.column("price").to_pylist() == [Decimal("9.99"), Decimal("19.95")]
        # JSON field is serialised to a string
        assert table.column("meta").to_pylist() == ['{"k": 1}', '{"k": 2}']
        assert pa.types.is_decimal(table.schema.field("price").type)

    def test_requires_fields_without_model(self):
        pytest.importorskip("pyarrow")
        with pytest.raises(ValueError):
            arrow_tools.queryset_to_arrow([])


class TestExportImportRoundtrip:
    def test_parquet_roundtrip(self, tmp_path):
        pytest.importorskip("pyarrow")
        path = tmp_path / "data.parquet"
        result = arrow_tools.export_queryset(make_queryset(), path, fields=FIELDS)
        assert result == str(path)
        assert path.exists()

        rows = arrow_tools.read_rows(path)
        assert rows[0][1] == "alpha"
        assert rows[1][0] == 2
        assert rows[0][6] == Decimal("9.99")

    def test_ipc_roundtrip(self, tmp_path):
        pytest.importorskip("pyarrow")
        path = tmp_path / "data.arrow"
        arrow_tools.export_queryset(make_queryset(), path, fields=FIELDS)
        rows = arrow_tools.read_rows(path)
        assert [row[1] for row in rows] == ["alpha", "beta"]

    def test_csv_roundtrip_and_import(self, tmp_path):
        path = tmp_path / "data.csv"
        result = arrow_tools.export_queryset(make_queryset(), path, fields=FIELDS, format="csv")
        assert result == str(path)
        text = path.read_text(encoding="utf-8")
        assert text.splitlines()[0].startswith("id,name,active")

        model = build_model()
        count = arrow_tools.import_to_model(path, model, fields=["id", "name"], batch_size=1)
        assert count == 2
        created = model.objects.created
        assert [(obj.id, obj.name) for obj in created] == [(1, "alpha"), (2, "beta")]

    def test_parquet_import_to_model(self, tmp_path):
        pytest.importorskip("pyarrow")
        path = tmp_path / "data.parquet"
        arrow_tools.export_queryset(make_queryset(), path, fields=FIELDS)
        model = build_model()
        count = arrow_tools.import_to_model(path, model, fields=["id", "name", "score"])
        assert count == 2
        assert model.objects.created[1].score == 2.5

    def test_plain_rows_export_parquet(self, tmp_path):
        pytest.importorskip("pyarrow")
        path = tmp_path / "plain.parquet"
        rows = [(1, "a"), (2, "b")]
        arrow_tools.export_queryset(rows, path, fields=["id", "name"])
        assert arrow_tools.read_rows(path) == [(1, "a"), (2, "b")]

    def test_empty_queryset_parquet(self, tmp_path):
        pytest.importorskip("pyarrow")
        path = tmp_path / "empty.parquet"
        arrow_tools.export_queryset(FakeQuerySet(build_model(), []), path, fields=FIELDS)
        table = arrow_tools.read_table(path)
        assert table.num_rows == 0

    def test_csv_json_roundtrip(self, tmp_path):
        path = tmp_path / "data.csv"
        arrow_tools.export_queryset(make_queryset(), path, fields=FIELDS, format="csv")
        rows = arrow_tools.read_rows(path)
        assert rows[0][FIELDS.index("meta")] == '{"k": 1}'
        model = build_model()
        arrow_tools.import_to_model(path, model, fields=FIELDS, batch_size=1)
        assert model.objects.created[0].meta == {"k": 1}
        assert model.objects.created[0].price == Decimal("9.99")

    def test_csv_import_coerces_types(self, tmp_path):
        path = tmp_path / "typed.csv"
        with open(path, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(FIELDS)
            writer.writerow(
                [
                    1,
                    "alpha",
                    "true",
                    "1.5",
                    "2026-01-02T03:04:05",
                    "2026-01-02",
                    "9.99",
                    '{"k": 1}',
                ]
            )
            writer.writerow([2, "", "false", "0", "", "", "", ""])
        model = build_model()
        arrow_tools.import_to_model(path, model, fields=FIELDS, batch_size=5)
        first, second = model.objects.created
        assert (first.id, first.active, first.score) == (1, True, 1.5)
        assert first.created == datetime(2026, 1, 2, 3, 4, 5)
        assert first.price == Decimal("9.99")
        assert first.meta == {"k": 1}
        assert second.name == ""
        assert second.active is False
        assert second.score == 0.0
        assert second.created is None


class TestNoPyArrowFallback:
    def test_has_arrow_false(self, monkeypatch):
        disable_arrow(monkeypatch)
        assert arrow_tools.has_arrow() is False

    def test_parquet_export_falls_back_to_csv(self, monkeypatch, tmp_path):
        disable_arrow(monkeypatch)
        path = tmp_path / "data.parquet"
        result = arrow_tools.export_queryset(make_queryset(), path, fields=FIELDS)
        assert result == str(tmp_path / "data.csv")
        assert not path.exists()
        assert (tmp_path / "data.csv").exists()

    def test_csv_still_works(self, monkeypatch, tmp_path):
        disable_arrow(monkeypatch)
        path = tmp_path / "data.csv"
        arrow_tools.export_queryset(make_queryset(), path, fields=FIELDS, format="csv")
        assert path.read_text(encoding="utf-8").startswith("id,")

    def test_arrow_only_helpers_raise(self, monkeypatch):
        disable_arrow(monkeypatch)
        with pytest.raises(arrow_tools.ArrowNotAvailable):
            arrow_tools.read_table("x.parquet")
        with pytest.raises(arrow_tools.ArrowNotAvailable):
            arrow_tools.queryset_to_arrow(make_queryset(), fields=FIELDS)
        assert arrow_tools.data_to_arrow({"a": 1}) is None

    def test_export_to_bytes_falls_back_to_csv(self, monkeypatch):
        disable_arrow(monkeypatch)
        content, content_type, extension = arrow_tools.export_queryset_to_bytes(make_queryset(), fields=FIELDS)
        assert extension == "csv"
        assert content_type == "text/csv"
        assert content.startswith(b"id,name")

    def test_parquet_import_requires_arrow(self, monkeypatch, tmp_path):
        disable_arrow(monkeypatch)
        path = tmp_path / "data.parquet"
        path.write_bytes(b"PAR1")
        with pytest.raises(arrow_tools.ArrowNotAvailable):
            arrow_tools.import_to_model(path, build_model(), fields=FIELDS)


class TestExportToBytes:
    def test_parquet_bytes(self):
        pytest.importorskip("pyarrow")
        content, content_type, extension = arrow_tools.export_queryset_to_bytes(
            make_queryset(), format="parquet", fields=FIELDS
        )
        assert extension == "parquet"
        assert content_type == "application/vnd.apache.parquet"
        assert content[:4] == b"PAR1"
        assert content[-4:] == b"PAR1"

    def test_arrow_bytes(self):
        pa = pytest.importorskip("pyarrow")
        content, content_type, extension = arrow_tools.export_queryset_to_bytes(
            make_queryset(), format="arrow", fields=FIELDS
        )
        assert extension == "arrow"
        assert content_type == "application/vnd.apache.arrow.stream"
        table = pa.ipc.open_stream(content).read_all()
        assert table.num_rows == 2


class TestViewDecorators:
    def test_dict_to_parquet_with_arrow(self):
        pytest.importorskip("pyarrow")
        from pytigon_lib.schviews.viewtools import dict_to_parquet

        @dict_to_parquet
        def view(request):
            return [{"a": 1}, {"a": 2}]

        response = view(None)
        assert response["Content-Type"] == "application/vnd.apache.parquet"
        assert response.content[:4] == b"PAR1"

    def test_dict_to_parquet_without_arrow(self, monkeypatch):
        disable_arrow(monkeypatch)
        from pytigon_lib.schviews.viewtools import dict_to_parquet

        @dict_to_parquet
        def view(request):
            return [{"a": 1}]

        response = view(None)
        assert response["Content-Type"] == "application/json"

    def test_dict_to_arrow_with_arrow(self):
        pytest.importorskip("pyarrow")
        from pytigon_lib.schviews.viewtools import dict_to_arrow

        @dict_to_arrow
        def view(request):
            return {"a": 1}

        response = view(None)
        assert response["Content-Type"] == "application/vnd.apache.arrow.stream"
