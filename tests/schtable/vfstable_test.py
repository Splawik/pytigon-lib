"""Tests for :mod:`pytigon_lib.schtable.vfstable` using mock VFS and Django."""

import datetime
import os
import tempfile
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

import django

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
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "test-cache",
            }
        },
        TEMP_PATH=tempfile.gettempdir(),
        DEFAULT_FILE_STORAGE="django.core.files.storage.InMemoryStorage",
    )
    django.setup()

from pytigon_lib.schtable.vfstable import (
    VfsTable,
    str_cmp,
    vfsconvert,
    vfsopen,
    vfsopen_page,
    vfssave,
    vfstable_view,
    vfsview,
)
from pytigon_lib.schtools.tools import bdecode, bencode


class TestStrCmpVfs:
    def test_dotdot_sorts_first_x(self):
        x = [".."]
        y = ["file.txt"]
        result = str_cmp(x, y, ((0, 1),))
        assert result == -1

    def test_dotdot_sorts_first_y(self):
        x = ["file.txt"]
        y = [".."]
        result = str_cmp(x, y, ((0, 1),))
        assert result == 1

    def test_tuple_dotdot(self):
        x = [("..", "#fff")]
        y = "file.txt"
        result = str_cmp(x, y, ((0, 1),))
        assert result == -1

    def test_y_tuple_dotdot(self):
        x = "file.txt"
        y = [("..", "#fff")]
        result = str_cmp(x, y, ((0, 1),))
        assert result == 1

    def test_string_vs_tuple(self):
        x = "file.txt"
        y = ("dir", "#fff")
        result = str_cmp(x, y, ((0, 1),))
        assert result == 1

    def test_tuple_vs_string(self):
        x = ("dir", "#fff")
        y = "file.txt"
        result = str_cmp(x, y, ((0, 1),))
        assert result == -1

    def test_string_compare_greater(self):
        x = "z"
        y = "a"
        result = str_cmp(x, y, ((0, 1),))
        assert result == 1

    def test_string_compare_less(self):
        x = "a"
        y = "z"
        result = str_cmp(x, y, ((0, 1),))
        assert result == -1

    def test_equal_single_level(self):
        x = "same"
        y = "same"
        result = str_cmp(x, y, ((0, 1),))
        assert result == 0

    def test_multi_level_second_decides(self):
        x = ("a", "z")
        y = ("a", "a")
        result = str_cmp(x, y, ((0, 1), (1, 1)))
        assert result == 1

    def test_multi_level_all_equal(self):
        x = ("a", "b")
        y = ("a", "b")
        result = str_cmp(x, y, ((0, 1), (1, 1)))
        assert result == 0

    def test_exception_returns_zero(self):
        import builtins
        class BadCompare:
            def __init__(self):
                self.val = "test"
            def __getitem__(self, key):
                return self.val
            def __gt__(self, other):
                raise Exception("boom")
            def __lt__(self, other):
                raise Exception("boom")
        x = BadCompare()
        y = BadCompare()
        result = str_cmp(x, y, ((0, 1),))
        assert result == 0


class TestVfsTableInit:
    def test_init_with_folder(self):
        vt = VfsTable("/data/docs")
        assert vt.folder == "/data/docs"
        assert vt.col_names == ["ID", "Name", "Size", "Created"]
        assert vt.col_types == ["int", "str", "int", "datetime"]
        assert vt.col_length == [10, 10, 10]
        assert vt.auto_cols == []

    def test_init_normalizes_path(self):
        vt = VfsTable("/data/../data/docs")
        assert vt.folder == "/data/docs"

    def test_set_task_href(self):
        vt = VfsTable("/")
        vt.set_task_href("/tasks/123")
        assert vt.task_href == "/tasks/123"


class TestVfsTableSizeToColor:
    def test_small_size(self):
        vt = VfsTable("/")
        assert vt._size_to_color(500) == "#fff"

    def test_medium_size(self):
        vt = VfsTable("/")
        assert vt._size_to_color(500000) == "#fdd"

    def test_large_size(self):
        vt = VfsTable("/")
        assert vt._size_to_color(2 * 1073741824) == "#000,#FFF"


class TestVfsTableTimeToColor:
    def test_today(self):
        vt = VfsTable("/")
        color = vt._time_to_color(datetime.datetime.today())
        assert "#F00" in color or "#f00" in color.lower() or "#FFF" in color

    def test_old_file(self):
        vt = VfsTable("/")
        color = vt._time_to_color(datetime.datetime.today() - datetime.timedelta(days=400))
        assert "#000,#FFF" in color or "#fff" in color.lower()

    def test_none_time(self):
        vt = VfsTable("/")
        color = vt._time_to_color(None)
        assert "#F00" in color or "#f00" in color.lower()


class TestVfsTableGetTable:
    def test_get_table_empty_dir(self):
        vt = VfsTable("/testdir")
        mock_fs = MagicMock()
        mock_fs.listdir.return_value = []
        mock_fs.isdir.return_value = False
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            result = vt._get_table()
            assert result == []

    def test_get_table_with_root_dotdot(self):
        vt = VfsTable("/")
        mock_fs = MagicMock()
        mock_fs.listdir.return_value = []
        mock_fs.isdir.return_value = False
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            result = vt._get_table()
            assert isinstance(result, list)

    def test_get_table_with_files(self):
        vt = VfsTable("/testdir")
        mock_fs = MagicMock()
        mock_fs.listdir.return_value = ["file.txt"]
        mock_fs.isdir.return_value = False
        mock_info = MagicMock()
        mock_info.size = 100
        mock_info.modified = datetime.datetime(2025, 6, 15, tzinfo=datetime.UTC)
        mock_info.raw = {"name": "file.txt", "size": 100, "type": "file"}
        mock_fs.getdetails.return_value = mock_info
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            result = vt._get_table()
            assert any(r[1] == "file.txt" for r in result)

    def test_get_table_with_directory(self):
        vt = VfsTable("/testdir")
        mock_fs = MagicMock()
        mock_fs.listdir.return_value = ["subdir"]
        mock_fs.isdir.return_value = True
        mock_info = MagicMock()
        mock_info.modified = datetime.datetime(2025, 6, 15, tzinfo=datetime.UTC)
        mock_info.raw = {"name": "subdir", "type": "directory"}
        mock_fs.getdetails.return_value = mock_info
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            result = vt._get_table()
            assert any(isinstance(r[1], tuple) for r in result)

    def test_get_table_with_value_filter(self):
        vt = VfsTable("/testdir")
        mock_fs = MagicMock()
        mock_fs.listdir.return_value = ["file.txt", "other.log"]
        mock_fs.isdir.return_value = False
        mock_info = MagicMock()
        mock_info.size = 100
        mock_info.modified = datetime.datetime(2025, 6, 15, tzinfo=datetime.UTC)
        mock_info.raw = {"name": "file.txt", "size": 100, "type": "file"}
        mock_fs.getdetails.return_value = mock_info
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            result = vt._get_table(value="file")
            assert "file.txt" in [r[1] if isinstance(r[1], str) else "" for r in result]

    def test_get_table_zip_treated_as_dir(self):
        vt = VfsTable("/testdir")
        mock_fs = MagicMock()
        mock_fs.listdir.return_value = ["archive.zip"]
        mock_fs.isdir.return_value = False
        mock_info = MagicMock()
        mock_info.modified = datetime.datetime(2025, 6, 15, tzinfo=datetime.UTC)
        mock_info.raw = {"name": "archive.zip", "type": "directory"}
        mock_fs.getdetails.return_value = mock_info
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            result = vt._get_table()
            assert any(isinstance(r[1], tuple) for r in result)

    def test_get_table_exception_handling(self):
        vt = VfsTable("/testdir")
        mock_fs = MagicMock()
        mock_fs.listdir.side_effect = Exception("VFS error")
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            result = vt._get_table()
            assert result == []


class TestVfsTablePage:
    def test_page_returns_list(self):
        vt = VfsTable("/testdir")
        mock_fs = MagicMock()
        mock_fs.listdir.return_value = []
        mock_fs.isdir.return_value = False
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            result = vt.page(0)
            assert isinstance(result, list)

    def test_page_pagination(self):
        vt = VfsTable("/testdir")
        mock_fs = MagicMock()
        entries = [f"file{i}.txt" for i in range(300)]
        mock_fs.listdir.return_value = entries
        mock_fs.isdir.return_value = False
        mock_info = MagicMock()
        mock_info.size = 100
        mock_info.modified = datetime.datetime(2025, 6, 15, tzinfo=datetime.UTC)
        mock_info.raw = {"name": "f.txt", "size": 100, "type": "file"}
        mock_fs.getdetails.return_value = mock_info
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            result = vt.page(0)
            assert len(result) <= 256

    def test_page_with_sort(self):
        vt = VfsTable("/testdir")
        mock_fs = MagicMock()
        mock_fs.listdir.return_value = ["b.txt", "a.txt"]
        mock_fs.isdir.return_value = False
        mock_info = MagicMock()
        mock_info.size = 100
        mock_info.modified = datetime.datetime(2025, 6, 15, tzinfo=datetime.UTC)
        mock_info.raw = {"name": "f.txt", "size": 100, "type": "file"}
        mock_fs.getdetails.return_value = mock_info
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            result = vt.page(0, sort="Name")
            assert isinstance(result, list)


class TestVfsTableCount:
    def test_count(self):
        vt = VfsTable("/testdir")
        mock_fs = MagicMock()
        mock_fs.listdir.return_value = ["a.txt", "b.txt"]
        mock_fs.isdir.return_value = False
        mock_info = MagicMock()
        mock_info.size = 100
        mock_info.modified = datetime.datetime(2025, 6, 15, tzinfo=datetime.UTC)
        mock_info.raw = {"name": "f.txt", "size": 100, "type": "file"}
        mock_fs.getdetails.return_value = mock_info
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            result = vt.count(None)
            assert result == 3


class TestVfsTableExecCommand:
    def test_mkdir(self):
        mock_fs = MagicMock()
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            vt = VfsTable("/testdir")
            result = vt.exec_command(("MKDIR", None, (bencode("/testdir"), bencode("newdir"))))
            assert isinstance(result, dict)

    def test_newfile(self):
        mock_fs = MagicMock()
        mock_fs.open.return_value = MagicMock()
        mock_fs.open.return_value.__enter__ = MagicMock(return_value=MagicMock())
        mock_fs.open.return_value.__exit__ = MagicMock(return_value=False)
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            vt = VfsTable("/testdir")
            result = vt.exec_command(("NEWFILE", None, (bencode("/testdir"), bencode("newfile.txt"))))
            assert isinstance(result, dict)

    def test_rename(self):
        mock_fs = MagicMock()
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            vt = VfsTable("/testdir")
            result = vt.exec_command(("RENAME", (bencode("/testdir/old.txt"),), (bencode("/testdir"), bencode("new.txt"))))
            assert isinstance(result, dict)

    def test_unknown_command(self):
        vt = VfsTable("/testdir")
        result = vt.exec_command(("UNKNOWN",))
        assert isinstance(result, dict)
        assert result == {}


class TestVfsTableInsertUpdateDelete:
    def test_insert_rec(self):
        vt = VfsTable("/")
        vt.insert_rec([])

    def test_update_rec(self):
        vt = VfsTable("/")
        vt.update_rec([])

    def test_delete_rec(self):
        vt = VfsTable("/")
        vt.delete_rec(0)

    def test_auto(self):
        vt = VfsTable("/")
        vt.auto("col", ["c1"], [1])


class TestVfsTableViewFunction:
    def test_get_request(self):
        from django.test import RequestFactory
        rf = RequestFactory()
        request = rf.get("/vfs/table/")
        with patch("pytigon_lib.schtable.vfstable.VfsTable.command") as mock_cmd:
            mock_cmd.return_value = "[]"
            from pytigon_lib.schtable.vfstable import vfstable_view
            response = vfstable_view(request, bencode("/"))
            assert response is not None
            assert response.status_code == 200

    def test_post_request(self):
        from django.test import RequestFactory
        rf = RequestFactory()
        request = rf.post("/vfs/table/", {"cmd": "1", "value": "null"})
        from pytigon_lib.schtable.vfstable import vfstable_view
        response = vfstable_view(request, bencode("/"))
        assert response is not None


class TestVfsOpenFunction:
    def test_opens_file(self):
        from django.test import RequestFactory
        import binascii
        mock_fs = MagicMock()
        mock_open = MagicMock()
        mock_open.__enter__ = MagicMock(return_value=MagicMock())
        mock_open.__enter__.return_value.read = MagicMock(return_value=b"test data")
        mock_open.__exit__ = MagicMock(return_value=False)
        mock_fs.open.return_value = mock_open
        rf = RequestFactory()
        request = rf.get("/vfs/open/")
        encoded = bencode("/test/file.txt")
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            response = vfsopen(request, encoded)
            assert response.status_code == 200

    def test_pdf_content_type(self):
        from django.test import RequestFactory
        mock_fs = MagicMock()
        mock_open = MagicMock()
        mock_open.__enter__ = MagicMock(return_value=MagicMock())
        mock_open.__enter__.return_value.read = MagicMock(return_value=b"%PDF")
        mock_open.__exit__ = MagicMock(return_value=False)
        mock_fs.open.return_value = mock_open
        rf = RequestFactory()
        request = rf.get("/vfs/open/")
        encoded = bencode("/test/file.pdf")
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            response = vfsopen(request, encoded)
            assert response["Content-Type"] == "application/pdf"

    def test_docx_content_type(self):
        from django.test import RequestFactory
        mock_fs = MagicMock()
        mock_open = MagicMock()
        mock_open.__enter__ = MagicMock(return_value=MagicMock())
        mock_open.__enter__.return_value.read = MagicMock(return_value=b"docx")
        mock_open.__exit__ = MagicMock(return_value=False)
        mock_fs.open.return_value = mock_open
        rf = RequestFactory()
        request = rf.get("/vfs/open/")
        encoded = bencode("/test/file.docx")
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            response = vfsopen(request, encoded)
            assert "wordprocessingml.document" in response["Content-Type"]

    def test_xlsx_content_type(self):
        from django.test import RequestFactory
        mock_fs = MagicMock()
        mock_open = MagicMock()
        mock_open.__enter__ = MagicMock(return_value=MagicMock())
        mock_open.__enter__.return_value.read = MagicMock(return_value=b"xlsx")
        mock_open.__exit__ = MagicMock(return_value=False)
        mock_fs.open.return_value = mock_open
        rf = RequestFactory()
        request = rf.get("/vfs/open/")
        encoded = bencode("/test/file.xlsx")
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            response = vfsopen(request, encoded)
            assert "spreadsheetml.sheet" in response["Content-Type"]

    def test_spdf_content_type(self):
        from django.test import RequestFactory
        mock_fs = MagicMock()
        mock_open = MagicMock()
        mock_open.__enter__ = MagicMock(return_value=MagicMock())
        mock_open.__enter__.return_value.read = MagicMock(return_value=b"spdf")
        mock_open.__exit__ = MagicMock(return_value=False)
        mock_fs.open.return_value = mock_open
        rf = RequestFactory()
        request = rf.get("/vfs/open/")
        encoded = bencode("/test/file.spdf")
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            response = vfsopen(request, encoded)
            assert response["Content-Type"] == "application/spdf"

    def test_exception_returns_empty(self):
        from django.test import RequestFactory
        mock_fs = MagicMock()
        mock_fs.open.side_effect = Exception("Error opening")
        rf = RequestFactory()
        request = rf.get("/vfs/open/")
        encoded = bencode("/test/file.txt")
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            response = vfsopen(request, encoded)
            assert response.status_code == 200


class TestVfsOpenPage:
    def test_open_page(self):
        from django.test import RequestFactory
        import binascii
        mock_fs = MagicMock()
        mock_file = MagicMock()
        mock_file.read = MagicMock(return_value=b"page data")
        mock_open = MagicMock()
        mock_open.__enter__ = MagicMock(return_value=mock_file)
        mock_open.__exit__ = MagicMock(return_value=False)
        mock_fs.open.return_value = mock_open
        rf = RequestFactory()
        request = rf.get("/vfs/open_page/")
        encoded = bencode("/test/file.txt")
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            response = vfsopen_page(request, encoded, "0")
            assert response.status_code == 200
            mock_file.seek.assert_called_once_with(0)
            mock_file.read.assert_called_once_with(4096)

    def test_open_page_exception(self):
        from django.test import RequestFactory
        mock_fs = MagicMock()
        mock_fs.open.side_effect = Exception("Error")
        rf = RequestFactory()
        request = rf.get("/vfs/open_page/")
        encoded = bencode("/test/file.txt")
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            response = vfsopen_page(request, encoded, "0")
            assert response.status_code == 200


class TestVfsSave:
    def test_save_file(self):
        from django.test import RequestFactory
        mock_fs = MagicMock()
        mock_open = MagicMock()
        mock_open.__enter__ = MagicMock(return_value=MagicMock())
        mock_open.__exit__ = MagicMock(return_value=False)
        mock_fs.open.return_value = mock_open
        rf = RequestFactory()
        request = rf.post("/vfs/save/", {"data": "hello world"})
        encoded = bencode("/test/file.txt")
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            response = vfssave(request, encoded)
            assert response.content == b"OK"

    def test_save_with_conversion(self):
        from django.test import RequestFactory
        mock_fs = MagicMock()
        mock_open = MagicMock()
        mock_open.__enter__ = MagicMock(return_value=MagicMock())
        mock_open.__exit__ = MagicMock(return_value=False)
        mock_fs.open.return_value = mock_open
        rf = RequestFactory()
        request = rf.post("/vfs/save/", {"data": "# Hello"})
        encoded = bencode("/test/file.html.md")
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            with patch("pytigon_lib.schtable.vfstable.convert_file") as mock_conv:
                response = vfssave(request, encoded)
                mock_conv.assert_called_once()
                assert response is not None

    def test_save_exception(self):
        from django.test import RequestFactory
        mock_fs = MagicMock()
        mock_fs.open.side_effect = Exception("write error")
        rf = RequestFactory()
        request = rf.post("/vfs/save/", {"data": "test"})
        encoded = bencode("/test/file.txt")
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            response = vfssave(request, encoded)
            assert b"ERROR" in response.content

    def test_save_no_post_data(self):
        from django.test import RequestFactory
        rf = RequestFactory()
        request = rf.post("/vfs/save/")
        encoded = bencode("/test/file.txt")
        response = vfssave(request, encoded)
        assert b"ERROR" in response.content


class TestVfsView:
    def test_view_ithm_file(self):
        from django.test import RequestFactory
        rf = RequestFactory()
        request = rf.get("/vfs/view/")
        encoded = bencode("/test/file.ithm")
        with patch("pytigon_lib.schtable.vfstable.vfsconvert") as mock_conv:
            mock_conv.return_value = MagicMock(status_code=200, content=b"converted")
            response = vfsview(request, encoded)
            assert response is not None

    def test_view_md_file(self):
        from django.test import RequestFactory
        rf = RequestFactory()
        request = rf.get("/vfs/view/")
        encoded = bencode("/test/file.md")
        with patch("pytigon_lib.schtable.vfstable.vfsconvert") as mock_conv:
            mock_conv.return_value = MagicMock(status_code=200, content=b"converted")
            response = vfsview(request, encoded)
            assert response is not None

    def test_view_plain_text(self):
        from django.test import RequestFactory
        mock_fs = MagicMock()
        mock_open = MagicMock()
        mock_open.__enter__ = MagicMock(return_value=MagicMock())
        mock_open.__enter__.return_value.read = MagicMock(return_value="plain text")
        mock_open.__exit__ = MagicMock(return_value=False)
        mock_fs.open.return_value = mock_open
        rf = RequestFactory()
        request = rf.get("/vfs/view/")
        encoded = bencode("/test/file.txt")
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            response = vfsview(request, encoded)
            assert b"plain text" in response.content

    def test_view_exception(self):
        from django.test import RequestFactory
        mock_fs = MagicMock()
        mock_fs.open.side_effect = Exception("read error")
        rf = RequestFactory()
        request = rf.get("/vfs/view/")
        encoded = bencode("/test/file.txt")
        with patch("pytigon_lib.schtable.vfstable.default_storage") as mock_storage:
            mock_storage.fs = mock_fs
            response = vfsview(request, encoded)
            assert response.status_code == 200


class TestVfsConvert:
    def test_convert_calls_convert_file(self):
        from django.test import RequestFactory
        rf = RequestFactory()
        request = rf.get("/vfs/convert/")
        encoded = bencode("/test/file.md")
        with patch("pytigon_lib.schtable.vfstable.convert_file") as mock_conv:
            mock_conv.return_value = True
            with patch("pytigon_lib.schtable.vfstable.io.BytesIO") as mock_buf:
                mock_buf.return_value.getvalue.return_value = b"converted data"
                response = vfsconvert(request, encoded, "pdf")
                assert response.status_code == 200
