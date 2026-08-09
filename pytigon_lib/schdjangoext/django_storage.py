from __future__ import annotations
import contextlib
import os
from urllib.parse import urljoin

from django.conf import settings
from django.core.files import File
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.deconstruct import deconstructible
from django.utils.encoding import filepath_to_uri

import posixpath
from datetime import datetime
from typing import Any
from urllib.parse import urljoin

from django.conf import settings
from django.core.files.base import File
from django.core.files.storage import Storage
from django.core.files.utils import validate_file_name
from django.utils import timezone
from django.utils.encoding import filepath_to_uri


# from pytigon_lib.schfs.adapters import _AutoCreateLocalFs, _fsspec_abspath, _fsspec_dirname
from pytigon_lib.schfs.adapters import FsspecMountFS, FsspecMultiFS, FsspecSimpleFS


class OSFS_EXT(FsspecSimpleFS):
    def __init__(self, path, **argv):
        super().__init__(path, **argv)


@deconstructible
class ThumbnailFileSystemStorage(FileSystemStorage):
    def __init__(self, location=None, base_url=None, *args, **kwargs):
        if location is None:
            location = settings.THUMBNAIL_MEDIA_ROOT or None
        if base_url is None:
            base_url = settings.THUMBNAIL_MEDIA_URL or None
        super().__init__(location, base_url, *args, **kwargs)

    def url(self, name):
        if self.base_url is None:
            raise ValueError("This file is not accessible via a URL.")
        url = filepath_to_uri(name)
        url = url.replace(settings.THUMBNAIL_MEDIA_ROOT, "")
        if url is not None:
            url = url.lstrip("/")
        return urljoin(self.base_url, url)


@deconstructible
class FSStorage(Storage):
    """Store Django files in an fsspec-compatible filesystem.

    By default, the filesystem is created by ``settings.DEFAULT_FILE_STORAGE_FS``.
    File names are always relative to the root of that filesystem. For example,
    when using ``FsspecMountFS``, a file may be saved as
    ``site_media/images/example.jpg``.

    ``base_url`` is the public URL prefix used by :meth:`url`. It normally maps
    to Django's ``MEDIA_URL`` setting. It does not need to resemble the physical
    fsspec path.
    """

    def __init__(self, fs: Any = None, base_url: str | None = None) -> None:
        if fs is None:
            fs = settings.DEFAULT_FILE_STORAGE_FS()

        self.fs = fs
        self.base_url = (
            base_url if base_url is not None else getattr(settings, "MEDIA_URL", None)
        )

        if self.base_url:
            self.base_url = self.base_url.rstrip("/") + "/"

    @staticmethod
    def validate_file_name(name: str, allow_relative_path: bool = True) -> bool:
        """Validate a file name to prevent path traversal attacks.

        Returns ``True`` when the name is safe to use, ``False`` otherwise.
        Absolute paths and any path segment equal to ``..`` are rejected so
        that user-supplied names cannot escape the storage root.
        """
        if not name:
            return True
        name = str(name).replace("\\", "/")
        if name.startswith("/"):
            return False
        if not allow_relative_path and "/" in name:
            return False
        if ".." in name.split("/"):
            return False
        return True

    def _clean_name(self, name: str) -> str:
        """Return a safe, normalised relative POSIX file name."""
        name = str(name).replace("\\", "/").strip("/")
        name = posixpath.normpath(name)

        if name in ("", "."):
            raise ValueError("The file name cannot be empty")
        if name == ".." or name.startswith("../"):
            raise SuspiciousFileOperation("The file name escapes the storage root")

        return name

    def _open(self, name: str, mode: str = "rb") -> File:
        """Open a stored file and wrap it in Django's File object."""
        name = self._clean_name(name)
        return File(self.fs.open(name, mode), name=name)

    def _save(self, name: str, content: File) -> str:
        """Save uploaded content, creating parent directories when necessary."""
        name = self._clean_name(name)
        validate_file_name(name, allow_relative_path=True)

        parent = posixpath.dirname(name)
        if parent:
            self.fs.makedirs(parent, exist_ok=True)

        # Exclusive mode prevents accidental overwrites if a name collision occurs
        # after Django has selected an available name.
        with self.fs.open(name, "xb") as destination:
            for chunk in content.chunks():
                destination.write(chunk)

        return name

    def delete(self, name: str) -> None:
        """Delete a file if it exists."""
        name = self._clean_name(name)
        if self.fs.exists(name):
            self.fs.rm(name)

    def exists(self, name: str) -> bool:
        """Return whether a file or directory exists."""
        return self.fs.exists(self._clean_name(name))

    def listdir(self, path: str) -> tuple[list[str], list[str]]:
        """Return directory names and file names directly below ``path``."""
        path = "" if not path else self._clean_name(path)
        directories: list[str] = []
        files: list[str] = []

        for entry in self.fs.ls(path, detail=True):
            if isinstance(entry, str):
                entry = self.fs.info(entry)

            entry_name = posixpath.basename(str(entry["name"]).rstrip("/"))
            if entry.get("type") == "directory":
                directories.append(entry_name)
            else:
                files.append(entry_name)

        return sorted(directories), sorted(files)

    def size(self, name: str) -> int:
        """Return the stored file size in bytes."""
        info = self.fs.info(self._clean_name(name))
        return int(info.get("size", 0))

    def url(self, name: str) -> str:
        """Return the public URL for a stored file."""
        if not self.base_url:
            raise ValueError("This storage has no base_url configured")

        name = self._clean_name(name)
        return urljoin(self.base_url, filepath_to_uri(name))

    def path(self, name: str) -> str:
        """Return a local path when the underlying filesystem supports it.

        Mounted, remote, and overlay filesystems do not have one meaningful
        operating-system path. They should be accessed through ``open()``.
        """
        name = self._clean_name(name)

        if getattr(self.fs, "protocol", None) in ("file", ("file", "local")):
            return self.fs._strip_protocol(name)

        raise NotImplementedError(
            "This fsspec storage does not expose a local operating-system path"
        )

    def get_accessed_time(self, name: str) -> datetime:
        """Return the last access time when provided by the backend."""
        return self._get_time(name, "atime", "accessed")

    def get_created_time(self, name: str) -> datetime:
        """Return the creation time when provided by the backend."""
        return self._get_time(name, "created", "ctime", "creation_time")

    def get_modified_time(self, name: str) -> datetime:
        """Return the modification time reported by the backend."""
        return self._get_time(name, "mtime", "LastModified", "modified")

    def _get_time(self, name: str, *keys: str) -> datetime:
        """Read and normalise a timestamp from fsspec's info dictionary."""
        info = self.fs.info(self._clean_name(name))
        value = next((info[key] for key in keys if info.get(key) is not None), None)

        if value is None:
            raise NotImplementedError(
                f"The filesystem does not provide timestamp metadata for {name!r}"
            )

        if isinstance(value, datetime):
            result = value
        elif isinstance(value, (int, float)):
            result = datetime.fromtimestamp(value, tz=timezone.utc)
        elif isinstance(value, str):
            result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            raise NotImplementedError(
                f"Unsupported timestamp value returned by filesystem: {value!r}"
            )

        if timezone.is_naive(result) and settings.USE_TZ:
            return timezone.make_aware(result, timezone.get_current_timezone())
        return result


# Imported lazily to avoid importing Django exceptions before the storage module
# is configured in projects that inspect this file without initialising Django.
from django.core.exceptions import SuspiciousFileOperation  # noqa: E402
