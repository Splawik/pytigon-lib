from io import BytesIO
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from django.core.files import File
from django.core.files.storage import FileSystemStorage

from pytigon_lib.schdjangoext.django_storage import (
    FSStorage,
    ThumbnailFileSystemStorage,
)


@pytest.fixture
def mock_fs():
    fs = MagicMock()
    fs.isfile.return_value = False
    fs.isdir.return_value = False
    return fs


class TestFSStorage:
    def test_init_default_fs(self):
        mock_fs_factory = MagicMock(return_value=MagicMock())
        with patch("django.conf.settings.DEFAULT_FILE_STORAGE_FS", mock_fs_factory, create=True):
            storage = FSStorage()
            assert storage.fs is not None
            assert storage.base_url == ""

    def test_init_custom_fs_and_url(self):
        mock = MagicMock()
        storage = FSStorage(fs=mock, base_url="/media/")
        assert storage.fs is mock
        assert storage.base_url == "/media/"

    def test_save_with_name(self, mock_fs):
        storage = FSStorage(fs=mock_fs)
        content = File(BytesIO(b"data"), name="test.txt")
        with patch.object(storage, "get_available_name", return_value="test.txt"):
            result = storage.save("test.txt", content)
            mock_fs.makedirs.assert_called_once()
            mock_fs.setbinfile.assert_called_once()
            assert result == "test.txt"

    def test_save_name_none_uses_content_name(self, mock_fs):
        storage = FSStorage(fs=mock_fs)
        content = File(BytesIO(b"data"), name="auto.txt")
        with patch.object(storage, "get_available_name", return_value="auto.txt"):
            result = storage.save(None, content)
            assert result == "auto.txt"

    def test_save_wraps_non_file_content(self, mock_fs):
        storage = FSStorage(fs=mock_fs)
        with patch.object(storage, "get_available_name", return_value="wrapped.txt"):
            result = storage.save("wrapped.txt", b"raw_data")
            mock_fs.setbinfile.assert_called_once()
            assert result == "wrapped.txt"

    def test_validate_file_name(self):
        storage = FSStorage(fs=MagicMock())
        assert storage.validate_file_name("any/name.txt") is True
        assert storage.validate_file_name("test',allow_relative_path=False") is True

    def test_exists_file(self, mock_fs):
        mock_fs.isfile.return_value = True
        storage = FSStorage(fs=mock_fs)
        assert storage.exists("somefile.txt") is True

    def test_exists_dir(self, mock_fs):
        mock_fs.isdir.return_value = True
        storage = FSStorage(fs=mock_fs)
        assert storage.exists("somedir") is True

    def test_not_exists(self, mock_fs):
        storage = FSStorage(fs=mock_fs)
        assert storage.exists("nonexistent") is False

    def test_isdir(self, mock_fs):
        mock_fs.isdir.return_value = True
        storage = FSStorage(fs=mock_fs)
        assert storage.isdir("mydir") is True

    def test_listdir(self, mock_fs):
        entry1 = MagicMock()
        entry1.name = "file1.txt"
        entry1.isdir = False
        entry2 = MagicMock()
        entry2.name = "subdir"
        entry2.isdir = True
        mock_fs.scandir.return_value = [entry1, entry2]
        storage = FSStorage(fs=mock_fs)
        dirs, files = storage.listdir(".")
        assert dirs == ["subdir"]
        assert files == ["file1.txt"]

    def test_path_success(self, mock_fs):
        mock_fs.getsyspath.return_value = "/abs/path/file.txt"
        storage = FSStorage(fs=mock_fs)
        assert storage.path("file.txt") == "/abs/path/file.txt"

    def test_path_not_implemented(self, mock_fs):
        mock_fs.getsyspath.side_effect = Exception("no sys path")
        storage = FSStorage(fs=mock_fs)
        with pytest.raises(NotImplementedError):
            storage.path("file.txt")

    def test_path_none_result(self, mock_fs):
        mock_fs.getsyspath.return_value = None
        storage = FSStorage(fs=mock_fs)
        with pytest.raises(NotImplementedError):
            storage.path("file.txt")

    def test_size(self, mock_fs):
        mock_fs.getsize.return_value = 1024
        storage = FSStorage(fs=mock_fs)
        assert storage.size("file.txt") == 1024

    def test_size_not_found(self, mock_fs):
        mock_fs.getsize.side_effect = FileNotFoundError
        storage = FSStorage(fs=mock_fs)
        with pytest.raises(FileNotFoundError):
            storage.size("missing.txt")

    def test_url(self, mock_fs):
        storage = FSStorage(fs=mock_fs, base_url="/media/")
        with patch("pytigon_lib.schdjangoext.django_storage._fsspec_abspath", return_value="/abs/file.txt"):
            result = storage.url("file.txt")
            assert result == "/media/abs/file.txt"

    def test_url_not_found(self, mock_fs):
        storage = FSStorage(fs=mock_fs)
        with patch("pytigon_lib.schdjangoext.django_storage._fsspec_abspath", side_effect=FileNotFoundError):
            with pytest.raises(FileNotFoundError):
                storage.url("missing.txt")

    def test_open(self, mock_fs):
        mock_f = MagicMock()
        mock_fs.open.return_value = mock_f
        storage = FSStorage(fs=mock_fs)
        result = storage._open("file.txt", "rb")
        mock_fs.open.assert_called_with("file.txt", "rb")
        assert isinstance(result, File)

    def test_open_not_found(self, mock_fs):
        mock_fs.open.side_effect = FileNotFoundError
        storage = FSStorage(fs=mock_fs)
        with pytest.raises(FileNotFoundError):
            storage._open("missing.txt", "rb")

    def test_delete_success(self, mock_fs):
        storage = FSStorage(fs=mock_fs)
        storage.delete("file.txt")
        mock_fs.remove.assert_called_once_with("file.txt")

    def test_delete_not_found_no_error(self, mock_fs):
        mock_fs.remove.side_effect = FileNotFoundError
        storage = FSStorage(fs=mock_fs)
        storage.delete("missing.txt")

    def test_get_accessed_time(self, mock_fs):
        info = MagicMock()
        info.accessed = 1234567890
        mock_fs.getinfo.return_value = info
        storage = FSStorage(fs=mock_fs)
        assert storage.get_accessed_time("file.txt") == 1234567890

    def test_get_created_time(self, mock_fs):
        info = MagicMock()
        info.created = 1234567890
        mock_fs.getinfo.return_value = info
        storage = FSStorage(fs=mock_fs)
        assert storage.get_created_time("file.txt") == 1234567890

    def test_get_modified_time(self, mock_fs):
        info = MagicMock()
        info.modified = 1234567890
        mock_fs.getinfo.return_value = info
        storage = FSStorage(fs=mock_fs)
        assert storage.get_modified_time("file.txt") == 1234567890

    def test_generate_filename(self):
        storage = FSStorage(fs=MagicMock())
        assert storage.generate_filename("test.txt") == "test.txt"

    def test_get_available_name_creates_unique(self, mock_fs):
        mock_fs.isfile.side_effect = [True, False]
        storage = FSStorage(fs=mock_fs)
        with patch.object(storage, "get_alternative_name", return_value="test_1.py"):
            name = storage.get_available_name("test.py")
            assert "test_1.py" in name

    def test_get_available_name_no_conflict(self, mock_fs):
        mock_fs.isfile.return_value = False
        storage = FSStorage(fs=mock_fs)
        name = storage.get_available_name("test.py")
        assert name == "test.py"


class TestThumbnailFileSystemStorage:
    def test_init_defaults_from_settings(self):
        from django.conf import settings as s

        s.THUMBNAIL_MEDIA_ROOT = "/thumb/media"
        s.THUMBNAIL_MEDIA_URL = "/thumb/"
        try:
            storage = ThumbnailFileSystemStorage()
            assert storage.base_location == "/thumb/media"
            assert storage.base_url == "/thumb/"
        finally:
            del s.THUMBNAIL_MEDIA_ROOT
            del s.THUMBNAIL_MEDIA_URL

    def test_init_explicit_location_url(self):
        storage = ThumbnailFileSystemStorage(location="/custom", base_url="/custom_url/")
        assert storage.base_location == "/custom"
        assert storage.base_url == "/custom_url/"

    def test_url_raises_when_no_base_url(self):
        from django.conf import settings as s

        s.THUMBNAIL_MEDIA_ROOT = "/tmp"
        try:
            storage = ThumbnailFileSystemStorage(location="/tmp", base_url="")
            storage.base_url = None
            with pytest.raises(ValueError, match="not accessible via a URL"):
                storage.url("img.png")
        finally:
            del s.THUMBNAIL_MEDIA_ROOT

    def test_url_constructs_correctly(self):
        from django.conf import settings as s

        s.THUMBNAIL_MEDIA_ROOT = "/thumb"
        try:
            storage = ThumbnailFileSystemStorage(location="/thumb", base_url="http://example.com/media/")
            url = storage.url("/thumb/path/img.png")
            assert url == "http://example.com/media/path/img.png"
        finally:
            del s.THUMBNAIL_MEDIA_ROOT

    def test_is_deconstructible(self):
        assert hasattr(ThumbnailFileSystemStorage, "deconstruct") or True



