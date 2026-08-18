"""
fsspec-based virtual filesystem adapters.

This module provides:

- FsspecSimpleFS: exposes one fsspec filesystem under an optional root path.
- FsspecMountFS: mounts multiple fsspec-compatible filesystems under
  logical directory paths.
- FsspecMultiFS: overlays multiple filesystems, using ordered lookup for
  reads and the first filesystem as the default write target.
"""

from __future__ import annotations

import contextlib
import copy
import os
import posixpath
from dataclasses import dataclass
from typing import Any

import fsspec
from fsspec import AbstractFileSystem


def _normalise_path(path: str | os.PathLike | None) -> str:
    """
    Normalises a logical path used within fsspec.

    Prevents escaping the mount root with ../.
    """
    if path is None:
        return ""

    value = str(path).replace("\\", "/").strip("/")
    if not value:
        return ""

    value = posixpath.normpath(value)
    if value in ("", "."):
        return ""
    if value == ".." or value.startswith("../"):
        raise ValueError(f"Path escapes filesystem root: {path!r}")

    return value.strip("/")


@dataclass(frozen=True)
class _Backend:
    fs: AbstractFileSystem
    root: str = ""

    def path(self, relative_path: str) -> str:
        relative_path = _normalise_path(relative_path)
        root = self.root.rstrip("/")
        if not root:
            return relative_path
        if not relative_path:
            return root
        return f"{root}/{relative_path}"


def _normalise_backend_root(path: str | os.PathLike | None) -> str:
    """Normalise a backend root while preserving absolute local paths."""
    if path is None:
        return ""

    value = str(path).replace("\\", "/")
    if not value or value == ".":
        return ""

    # A backend root is not a user-controlled logical path. In particular,
    # LocalFileSystem needs an absolute path to remain absolute.
    normalised = posixpath.normpath(value)
    return "" if normalised == "." else normalised.rstrip("/")


def _as_backend(
    filesystem: AbstractFileSystem | str | tuple[AbstractFileSystem, str],
    root: str | None = None,
) -> _Backend:
    """
    Converts the input into a _Backend instance.

    Supported values:
    - an fsspec filesystem, for example fsspec.filesystem("file")
    - a local path, for example "/srv/project/media"
    - an fsspec URL, for example "s3://bucket/media"
    - a tuple: (filesystem, "root/path/inside/filesystem")
    """
    if isinstance(filesystem, tuple):
        fs, tuple_root = filesystem
        if not isinstance(fs, AbstractFileSystem):
            raise TypeError(
                "First item in filesystem tuple must be an fsspec filesystem"
            )
        return _Backend(fs=fs, root=_normalise_backend_root(root or tuple_root))

    if isinstance(filesystem, AbstractFileSystem):
        return _Backend(fs=filesystem, root=_normalise_backend_root(root))

    if not isinstance(filesystem, str):
        raise TypeError(
            "filesystem must be an fsspec AbstractFileSystem, path, URL or (fs, root) tuple"
        )

    fs, fs_root = fsspec.core.url_to_fs(filesystem)
    effective_root = root if root is not None else fs_root

    return _Backend(fs=fs, root=_normalise_backend_root(effective_root))


def _is_write_mode(mode: str) -> bool:
    return any(flag in mode for flag in ("w", "a", "x", "+"))


class FsspecSimpleFS(AbstractFileSystem):
    """Expose one fsspec filesystem below an optional root path.

    This adapter is useful when a local directory or an fsspec URL should be
    treated as an independent filesystem before it is mounted in
    :class:`FsspecMountFS` or added to :class:`FsspecMultiFS`.

    Examples:
        local_media = FsspecSimpleFS("/srv/project/media")
        object_store = FsspecSimpleFS("s3://example-bucket/project-media")

        mounts.mount("site_media", local_media)
        static_files.add_fs("project_static", local_media)
    """

    protocol = "simple"

    def __init__(
        self,
        filesystem: AbstractFileSystem | str = "file",
        root: str | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._backend = _as_backend(filesystem, root)

    @classmethod
    def _strip_protocol(cls, path: str) -> str:
        return path[len("simple://") :] if path.startswith("simple://") else path

    @property
    def root(self) -> str:
        """The root path inside the wrapped filesystem."""
        return self._backend.root

    @property
    def filesystem(self) -> AbstractFileSystem:
        """The wrapped fsspec filesystem instance."""
        return self._backend.fs

    def _path(self, path: str) -> str:
        return self._backend.path(_normalise_path(path))

    def _logical_name(self, backend_name: str) -> str:
        name = str(backend_name).replace("\\", "/")
        root = self.root.rstrip("/")
        if root and name == root:
            return ""
        if root and name.startswith(f"{root}/"):
            return name[len(root) + 1 :]
        return name.strip("/")

    def _open(
        self,
        path: str,
        mode: str = "rb",
        block_size: int | None = None,
        autocommit: bool = True,
        cache_options: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        path = _normalise_path(path)
        if _is_write_mode(mode):
            parent = posixpath.dirname(path)
            if parent:
                self._backend.fs.makedirs(self._path(parent), exist_ok=True)
        return self._backend.fs.open(
            self._path(path),
            mode=mode,
            block_size=block_size,
            autocommit=autocommit,
            cache_options=cache_options,
            **kwargs,
        )

    def exists(self, path: str, **kwargs: Any) -> bool:
        return self._backend.fs.exists(self._path(path), **kwargs)

    def info(self, path: str, **kwargs: Any) -> dict[str, Any]:
        logical_path = _normalise_path(path)
        result = copy.deepcopy(
            self._backend.fs.info(self._path(logical_path), **kwargs)
        )
        result["name"] = logical_path
        return result

    def ls(
        self, path: str, detail: bool = True, **kwargs: Any
    ) -> list[dict[str, Any]] | list[str]:
        logical_path = _normalise_path(path)
        entries = self._backend.fs.ls(self._path(logical_path), detail=True, **kwargs)
        result: list[dict[str, Any]] = []
        for entry in entries:
            if isinstance(entry, str):
                entry = self._backend.fs.info(entry)
            item = copy.deepcopy(entry)
            item["name"] = self._logical_name(item["name"])
            result.append(item)
        return result if detail else [item["name"] for item in result]

    def find(
        self,
        path: str,
        maxdepth: int | None = None,
        withdirs: bool = False,
        detail: bool = False,
        **kwargs: Any,
    ) -> dict[str, dict[str, Any]] | list[str]:
        entries = self._backend.fs.find(
            self._path(path),
            maxdepth=maxdepth,
            withdirs=withdirs,
            detail=True,
            **kwargs,
        )
        result: dict[str, dict[str, Any]] = {}
        for backend_name, entry in entries.items():
            name = self._logical_name(backend_name)
            item = copy.deepcopy(entry)
            item["name"] = name
            result[name] = item
        return result if detail else sorted(result)

    def mkdir(self, path: str, create_parents: bool = True, **kwargs: Any) -> None:
        self._backend.fs.mkdir(
            self._path(path), create_parents=create_parents, **kwargs
        )

    def makedirs(self, path: str, exist_ok: bool = False) -> None:
        self._backend.fs.makedirs(self._path(path), exist_ok=exist_ok)

    def rm(
        self,
        path: str | list[str],
        recursive: bool = False,
        maxdepth: int | None = None,
        **kwargs: Any,
    ) -> None:
        paths = [
            self._path(item) for item in ([path] if isinstance(path, str) else path)
        ]
        self._backend.fs.rm(paths, recursive=recursive, maxdepth=maxdepth, **kwargs)

    def touch(self, path: str, truncate: bool = True, **kwargs: Any) -> None:
        logical_path = _normalise_path(path)
        parent = posixpath.dirname(logical_path)
        if parent:
            self._backend.fs.makedirs(self._path(parent), exist_ok=True)
        self._backend.fs.touch(self._path(logical_path), truncate=truncate, **kwargs)

    def cp_file(self, path1: str, path2: str, **kwargs: Any) -> None:
        destination_parent = posixpath.dirname(_normalise_path(path2))
        if destination_parent:
            self.makedirs(destination_parent, exist_ok=True)
        self._backend.fs.cp_file(self._path(path1), self._path(path2), **kwargs)

    def mv(
        self,
        path1: str,
        path2: str,
        recursive: bool = False,
        maxdepth: int | None = None,
        **kwargs: Any,
    ) -> None:
        destination_parent = posixpath.dirname(_normalise_path(path2))
        if destination_parent:
            self.makedirs(destination_parent, exist_ok=True)
        self._backend.fs.mv(
            self._path(path1),
            self._path(path2),
            recursive=recursive,
            maxdepth=maxdepth,
            **kwargs,
        )


class _AutoCreateLocalFs(FsspecSimpleFS):
    """A local filesystem rooted at ``root_path`` that is created on demand.

    This is the fsspec replacement for PyFilesystem2's ``OSFS``/``OSFS_EXT``:
    it exposes a local directory as a single fsspec filesystem whose root is
    auto-created when the instance is built. Relative paths are confined to
    ``root_path``; absolute paths remain absolute.
    """

    def __init__(self, root_path: str, auto_mkdir: bool = True, **kwargs: Any) -> None:
        if not isinstance(root_path, str) or not root_path:
            raise ValueError("root_path must be a non-empty path")
        absolute = os.path.abspath(root_path)
        if auto_mkdir:
            with contextlib.suppress(OSError):
                os.makedirs(absolute, exist_ok=True)
        kwargs.setdefault("auto_mkdir", auto_mkdir)
        super().__init__(absolute, **kwargs)


class FsspecMultiFS(AbstractFileSystem):
    """
    Overlay filesystem.

    Read operations:
        The file is searched for in the order in which filesystems
        were added with add_fs().

    Write operations:
        Files are written to the first added filesystem.
    """

    protocol = "multi"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._filesystems: list[tuple[str, _Backend]] = []

    @classmethod
    def _strip_protocol(cls, path: str) -> str:
        return path[len("multi://") :] if path.startswith("multi://") else path

    def add_fs(
        self,
        name: str,
        filesystem: AbstractFileSystem | str | tuple[AbstractFileSystem, str],
        root: str | None = None,
    ) -> None:
        """Adds a filesystem layer to the overlay filesystem."""
        if not name:
            raise ValueError("Filesystem name cannot be empty")
        if any(existing_name == name for existing_name, _ in self._filesystems):
            raise ValueError(f"Filesystem {name!r} has already been added")
        self._filesystems.append((name, _as_backend(filesystem, root)))

    @property
    def filesystems(self) -> tuple[str, ...]:
        """Filesystem names in lookup priority order."""
        return tuple(name for name, _ in self._filesystems)

    def _require_write_backend(self) -> _Backend:
        if not self._filesystems:
            raise RuntimeError("No filesystems have been added to FsspecMultiFS")
        return self._filesystems[0][1]

    def _find_backend(self, path: str) -> _Backend | None:
        path = _normalise_path(path)
        for _, backend in self._filesystems:
            try:
                if backend.fs.exists(backend.path(path)):
                    return backend
            except OSError:
                continue
        return None

    def _open(
        self,
        path: str,
        mode: str = "rb",
        block_size: int | None = None,
        autocommit: bool = True,
        cache_options: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        path = _normalise_path(path)
        if _is_write_mode(mode):
            backend = self._require_write_backend()
            parent = posixpath.dirname(path)
            if parent:
                backend.fs.makedirs(backend.path(parent), exist_ok=True)
        else:
            backend = self._find_backend(path)
            if backend is None:
                raise FileNotFoundError(path)
        return backend.fs.open(
            backend.path(path),
            mode=mode,
            block_size=block_size,
            autocommit=autocommit,
            cache_options=cache_options,
            **kwargs,
        )

    def exists(self, path: str, **kwargs: Any) -> bool:
        return self._find_backend(path) is not None

    def info(self, path: str, **kwargs: Any) -> dict[str, Any]:
        path = _normalise_path(path)
        backend = self._find_backend(path)
        if backend is None:
            raise FileNotFoundError(path)
        result = copy.deepcopy(backend.fs.info(backend.path(path), **kwargs))
        result["name"] = path
        return result

    def ls(
        self, path: str, detail: bool = True, **kwargs: Any
    ) -> list[dict[str, Any]] | list[str]:
        path = _normalise_path(path)
        entries: dict[str, dict[str, Any]] = {}
        for _, backend in self._filesystems:
            try:
                items = backend.fs.ls(backend.path(path), detail=True, **kwargs)
            except (FileNotFoundError, OSError):
                continue
            for item in items:
                if isinstance(item, str):
                    item = backend.fs.info(item)
                logical_name = (
                    f"{path}/{posixpath.basename(str(item['name']).rstrip('/'))}"
                    if path
                    else posixpath.basename(str(item["name"]).rstrip("/"))
                )
                if logical_name not in entries:
                    entry = copy.deepcopy(item)
                    entry["name"] = logical_name
                    entries[logical_name] = entry
        if not entries and path and not self.exists(path):
            raise FileNotFoundError(path)
        return list(entries.values()) if detail else list(entries)

    def find(
        self,
        path: str,
        maxdepth: int | None = None,
        withdirs: bool = False,
        detail: bool = False,
        **kwargs: Any,
    ) -> dict[str, dict[str, Any]] | list[str]:
        path = _normalise_path(path)
        found: dict[str, dict[str, Any]] = {}
        for _, backend in self._filesystems:
            try:
                items = backend.fs.find(
                    backend.path(path),
                    maxdepth=maxdepth,
                    withdirs=withdirs,
                    detail=True,
                    **kwargs,
                )
            except (FileNotFoundError, OSError):
                continue
            for backend_name, item in items.items():
                backend_name = str(backend_name).replace("\\", "/")
                root = backend.root.rstrip("/")
                relative_name = (
                    backend_name[len(root) + 1 :]
                    if root and backend_name.startswith(f"{root}/")
                    else backend_name.strip("/")
                )
                if relative_name not in found:
                    entry = copy.deepcopy(item)
                    entry["name"] = relative_name
                    found[relative_name] = entry
        return found if detail else sorted(found)

    def mkdir(self, path: str, create_parents: bool = True, **kwargs: Any) -> None:
        backend = self._require_write_backend()
        backend.fs.mkdir(backend.path(path), create_parents=create_parents, **kwargs)

    def makedirs(self, path: str, exist_ok: bool = False) -> None:
        backend = self._require_write_backend()
        backend.fs.makedirs(backend.path(path), exist_ok=exist_ok)

    def rm(
        self,
        path: str | list[str],
        recursive: bool = False,
        maxdepth: int | None = None,
        **kwargs: Any,
    ) -> None:
        for item in [path] if isinstance(path, str) else path:
            backend = self._find_backend(item)
            if backend is None:
                raise FileNotFoundError(item)
            backend.fs.rm(
                backend.path(item), recursive=recursive, maxdepth=maxdepth, **kwargs
            )

    def touch(self, path: str, truncate: bool = True, **kwargs: Any) -> None:
        backend = self._require_write_backend()
        parent = posixpath.dirname(_normalise_path(path))
        if parent:
            backend.fs.makedirs(backend.path(parent), exist_ok=True)
        backend.fs.touch(backend.path(path), truncate=truncate, **kwargs)

    def cp_file(self, path1: str, path2: str, **kwargs: Any) -> None:
        source = self._find_backend(path1)
        target = self._require_write_backend()
        if source is None:
            raise FileNotFoundError(path1)
        parent = posixpath.dirname(_normalise_path(path2))
        if parent:
            target.fs.makedirs(target.path(parent), exist_ok=True)
        if source.fs is target.fs:
            target.fs.cp_file(source.path(path1), target.path(path2), **kwargs)
            return
        with (
            source.fs.open(source.path(path1), "rb") as src,
            target.fs.open(target.path(path2), "wb") as dst,
        ):
            while chunk := src.read(1024 * 1024):
                dst.write(chunk)

    def mv(
        self,
        path1: str,
        path2: str,
        recursive: bool = False,
        maxdepth: int | None = None,
        **kwargs: Any,
    ) -> None:
        source = self._find_backend(path1)
        target = self._require_write_backend()
        if source is None:
            raise FileNotFoundError(path1)
        if source.fs is target.fs:
            target.fs.mv(
                source.path(path1),
                target.path(path2),
                recursive=recursive,
                maxdepth=maxdepth,
                **kwargs,
            )
            return
        self.cp_file(path1, path2, **kwargs)
        source.fs.rm(source.path(path1), recursive=recursive, maxdepth=maxdepth)


class FsspecMountFS(AbstractFileSystem):
    """
    Virtual filesystem that mounts other filesystems under selected paths.

    Example:
        root_fs = FsspecMountFS()
        root_fs.mount("static", "/srv/project/static")
        root_fs.mount("data", "s3://my-bucket/project-data")
    """

    protocol = "mount"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._mounts: dict[str, _Backend] = {}

    @classmethod
    def _strip_protocol(cls, path: str) -> str:
        return path[len("mount://") :] if path.startswith("mount://") else path

    def mount(
        self,
        mount_path: str,
        filesystem: AbstractFileSystem | str | tuple[AbstractFileSystem, str],
        root: str | None = None,
    ) -> None:
        """Mounts a filesystem under ``mount_path``."""
        mount_path = _normalise_path(mount_path)
        if not mount_path:
            raise ValueError("Mount path cannot be empty")
        if mount_path in self._mounts:
            raise ValueError(f"Mount path {mount_path!r} already exists")
        self._mounts[mount_path] = _as_backend(filesystem, root)

    def unmount(self, mount_path: str) -> None:
        """Removes a mount."""
        del self._mounts[_normalise_path(mount_path)]

    @property
    def mounts(self) -> tuple[str, ...]:
        """Returns all configured mount paths."""
        return tuple(sorted(self._mounts))

    def _resolve(self, path: str) -> tuple[_Backend, str]:
        path = _normalise_path(path)
        matches = [
            mount
            for mount in self._mounts
            if path == mount or path.startswith(f"{mount}/")
        ]
        if not matches:
            raise FileNotFoundError(f"No filesystem mounted for path: {path!r}")
        mount = max(matches, key=len)
        return self._mounts[mount], "" if path == mount else path[len(mount) + 1 :]

    def _virtual_directory_info(self, path: str) -> dict[str, Any] | None:
        path = _normalise_path(path)
        if (
            not path
            or path in self._mounts
            or any(mount.startswith(f"{path}/") for mount in self._mounts)
        ):
            return {"name": path, "type": "directory", "size": 0}
        return None

    def _virtual_children(self, path: str) -> list[str]:
        path = _normalise_path(path)
        prefix = f"{path}/" if path else ""
        return sorted(
            {
                mount[len(prefix) :].split("/", 1)[0]
                for mount in self._mounts
                if mount.startswith(prefix)
            }
        )

    def _open(
        self,
        path: str,
        mode: str = "rb",
        block_size: int | None = None,
        autocommit: bool = True,
        cache_options: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Any:
        backend, relative = self._resolve(path)
        if _is_write_mode(mode):
            parent = posixpath.dirname(relative)
            if parent:
                backend.fs.makedirs(backend.path(parent), exist_ok=True)
        return backend.fs.open(
            backend.path(relative),
            mode=mode,
            block_size=block_size,
            autocommit=autocommit,
            cache_options=cache_options,
            **kwargs,
        )

    def exists(self, path: str, **kwargs: Any) -> bool:
        if self._virtual_directory_info(path) is not None:
            return True
        try:
            backend, relative = self._resolve(path)
        except FileNotFoundError:
            return False
        return backend.fs.exists(backend.path(relative), **kwargs)

    def info(self, path: str, **kwargs: Any) -> dict[str, Any]:
        path = _normalise_path(path)
        virtual = self._virtual_directory_info(path)
        if virtual is not None:
            return virtual
        backend, relative = self._resolve(path)
        result = copy.deepcopy(backend.fs.info(backend.path(relative), **kwargs))
        result["name"] = path
        return result

    def ls(
        self, path: str, detail: bool = True, **kwargs: Any
    ) -> list[dict[str, Any]] | list[str]:
        path = _normalise_path(path)
        result: dict[str, dict[str, Any]] = {}
        # Virtual directories created by mounts.
        for child in self._virtual_children(path):
            name = f"{path}/{child}" if path else child
            result[name] = {"name": name, "type": "directory", "size": 0}
        try:
            backend, relative = self._resolve(path)
            entries = backend.fs.ls(backend.path(relative), detail=True, **kwargs)
        except (FileNotFoundError, OSError):
            entries = []
        for entry in entries:
            if isinstance(entry, str):
                entry = backend.fs.info(entry)
            name = (
                f"{path}/{posixpath.basename(str(entry['name']).rstrip('/'))}"
                if path
                else posixpath.basename(str(entry["name"]).rstrip("/"))
            )
            item = copy.deepcopy(entry)
            item["name"] = name
            result[name] = item
        if not result and not self.exists(path):
            raise FileNotFoundError(path)
        return list(result.values()) if detail else list(result)

    def find(
        self,
        path: str,
        maxdepth: int | None = None,
        withdirs: bool = False,
        detail: bool = False,
        **kwargs: Any,
    ) -> dict[str, dict[str, Any]] | list[str]:
        backend, relative = self._resolve(path)
        entries = backend.fs.find(
            backend.path(relative),
            maxdepth=maxdepth,
            withdirs=withdirs,
            detail=True,
            **kwargs,
        )
        result: dict[str, dict[str, Any]] = {}
        root = backend.root.rstrip("/")
        for backend_name, entry in entries.items():
            name = str(backend_name).replace("\\", "/")
            logical = (
                name[len(root) + 1 :]
                if root and name.startswith(f"{root}/")
                else name.strip("/")
            )
            item = copy.deepcopy(entry)
            item["name"] = logical
            result[logical] = item
        return result if detail else sorted(result)

    def mkdir(self, path: str, create_parents: bool = True, **kwargs: Any) -> None:
        backend, relative = self._resolve(path)
        backend.fs.mkdir(
            backend.path(relative), create_parents=create_parents, **kwargs
        )

    def makedirs(self, path: str, exist_ok: bool = False) -> None:
        backend, relative = self._resolve(path)
        backend.fs.makedirs(backend.path(relative), exist_ok=exist_ok)

    def rm(
        self,
        path: str | list[str],
        recursive: bool = False,
        maxdepth: int | None = None,
        **kwargs: Any,
    ) -> None:
        for item in [path] if isinstance(path, str) else path:
            item = _normalise_path(item)
            if item in self._mounts:
                raise PermissionError(f"Removing mount root is not allowed: {item!r}")
            backend, relative = self._resolve(item)
            backend.fs.rm(
                backend.path(relative), recursive=recursive, maxdepth=maxdepth, **kwargs
            )

    def touch(self, path: str, truncate: bool = True, **kwargs: Any) -> None:
        backend, relative = self._resolve(path)
        parent = posixpath.dirname(relative)
        if parent:
            backend.fs.makedirs(backend.path(parent), exist_ok=True)
        backend.fs.touch(backend.path(relative), truncate=truncate, **kwargs)

    def cp_file(self, path1: str, path2: str, **kwargs: Any) -> None:
        source, source_relative = self._resolve(path1)
        target, target_relative = self._resolve(path2)
        parent = posixpath.dirname(target_relative)
        if parent:
            target.fs.makedirs(target.path(parent), exist_ok=True)
        if source.fs is target.fs:
            target.fs.cp_file(
                source.path(source_relative), target.path(target_relative), **kwargs
            )
            return
        with (
            source.fs.open(source.path(source_relative), "rb") as src,
            target.fs.open(target.path(target_relative), "wb") as dst,
        ):
            while chunk := src.read(1024 * 1024):
                dst.write(chunk)

    def mv(
        self,
        path1: str,
        path2: str,
        recursive: bool = False,
        maxdepth: int | None = None,
        **kwargs: Any,
    ) -> None:
        source, source_relative = self._resolve(path1)
        target, target_relative = self._resolve(path2)
        if source.fs is target.fs:
            target.fs.mv(
                source.path(source_relative),
                target.path(target_relative),
                recursive=recursive,
                maxdepth=maxdepth,
                **kwargs,
            )
            return
        self.cp_file(path1, path2, **kwargs)
        source.fs.rm(
            source.path(source_relative), recursive=recursive, maxdepth=maxdepth
        )

    def getsyspath(self, path):
        backend, path2 = self._resolve(path)
        return backend.fs._path(path2)
