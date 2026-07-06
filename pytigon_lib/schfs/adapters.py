"""Adapter layer replacing PyFilesystem2 (fs) with fsspec.

Provides MountFS-like composite (FsspecMountFS), MultiFS-like composite
(FsspecMultiFS), and a local-fs adapter with API-compatible wrappers
that expose the same interface the rest of the codebase expects.
"""

import contextlib
import datetime
import os
from functools import cached_property
from typing import Any

from fsspec.implementations.local import LocalFileSystem


class _FsspecInfo:
    """Mimics fs.info objects returned by PyFilesystem2's getinfo/getdetails."""

    def __init__(self, info: dict[str, Any]) -> None:
        self._info = info

    @cached_property
    def size(self) -> int:
        return self._info.get("size", 0)

    @cached_property
    def modified(self) -> datetime.datetime | None:
        ts = self._info.get("mtime") or self._info.get("LastModified")
        if ts is None:
            return None
        if isinstance(ts, datetime.datetime):
            return ts
        return datetime.datetime.fromtimestamp(float(ts), tz=datetime.UTC)

    @cached_property
    def created(self) -> datetime.datetime | None:
        ts = self._info.get("created") or self._info.get("CreationTime")
        if ts is None:
            return None
        if isinstance(ts, datetime.datetime):
            return ts
        return datetime.datetime.fromtimestamp(float(ts), tz=datetime.UTC)

    @cached_property
    def accessed(self) -> datetime.datetime | None:
        ts = self._info.get("atime") or self._info.get("LastAccessTime")
        if ts is None:
            return None
        if isinstance(ts, datetime.datetime):
            return ts
        return datetime.datetime.fromtimestamp(float(ts), tz=datetime.UTC)

    @cached_property
    def isdir(self) -> bool:
        return self._info.get("type") == "directory"

    @cached_property
    def name(self) -> str:
        return (self._info.get("name") or "").rstrip("/").rsplit("/", 1)[-1]

    @cached_property
    def raw(self) -> dict[str, Any]:
        return dict(self._info)


class _FsspecInfoExt(_FsspecInfo):
    """Extended info exposing ``type`` and ``size`` as top-level keys (used by VfsTable)."""

    @cached_property
    def type(self) -> str:
        return self._info.get("type", "")

    @cached_property
    def size(self) -> int:
        return self._info.get("size", 0)


class _AutoCreateLocalFs(LocalFileSystem):
    """LocalFileSystem variant that auto-creates directories on init (mirrors OSFS_EXT behaviour)."""

    def __init__(self, root_path: str, auto_mkdir: bool = True, **kwargs: Any) -> None:
        super().__init__(auto_mkdir=auto_mkdir, **kwargs)
        self._root = os.path.abspath(root_path)


class FsspecMountFS:
    """Read-only composite filesystem that routes paths by mount prefix (like PyFilesystem2 MountFS).

    Mounts are registered with ``mount(prefix, fs)`` — the *prefix* does NOT include
    a leading ``/`` (e.g. ``"pytigon"``, ``"static"``).  Paths arriving at method calls
    are expected to have a leading ``/``; the first segment is stripped and used to
    dispatch to the registered sub-filesystem.
    """

    def __init__(self) -> None:
        self._mounts: dict[str, Any] = {}
        self._order: list[str] = []

    def mount(self, name: str, fs: Any) -> None:
        name = name.strip("/")
        self._mounts[name] = fs
        if name not in self._order:
            self._order.append(name)

    def add_fs(self, name: str, fs: Any) -> None:
        if name in self._mounts:
            if isinstance(self._mounts[name], FsspecMultiFS):
                self._mounts[name].add_fs(name, fs)
                return
            existing = self._mounts[name]
            mfs = FsspecMultiFS()
            mfs.add_fs(name, existing)
            mfs.add_fs(name, fs)
            self._mounts[name] = mfs
        else:
            self._mounts[name] = fs
            self._order.append(name)

    @property
    def mounts(self) -> list[tuple[str, Any]]:
        return [(f"/{name}/", fs) for name, fs in self._mounts.items()]

    def _resolve(self, path: str) -> tuple[Any, str]:
        path = str(path)
        if path.startswith("/"):
            path = path[1:]
        if not path:
            return self._mounts.get(self._order[0]) if self._order else (None, "/")
        parts = path.split("/", 1)
        prefix = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
        fs = self._mounts.get(prefix)
        if fs is None:
            if self._order:
                fs = self._mounts[self._order[0]]
                rest = path
            else:
                return None, ""
        return fs, rest

    def _resolve_mount_name(self, path: str) -> tuple[str, str | None]:
        path = str(path)
        if path.startswith("/"):
            path = path[1:]
        if not path:
            return self._order[0] if self._order else ("", "/")
        parts = path.split("/", 1)
        prefix = parts[0]
        rest = parts[1] if len(parts) > 1 else ""
        if prefix not in self._mounts:
            return (self._order[0] if self._order else "", path)
        return prefix, rest

    def open(self, path: str, mode: str = "rb", **kwargs: Any) -> Any:
        fs, rest = self._resolve(path)
        if fs is None:
            raise FileNotFoundError(path)
        if hasattr(fs, "open"):
            return fs.open(rest or "/", mode, **kwargs)
        return fs._open(rest or "/", mode, **kwargs)

    def isfile(self, path: str) -> bool:
        fs, rest = self._resolve(path)
        if fs is None or not rest:
            return False
        if hasattr(fs, "isfile"):
            return fs.isfile(rest)
        return fs.isfile(rest)

    def isdir(self, path: str) -> bool:
        fs, rest = self._resolve(path)
        if fs is None:
            return False
        if not rest:
            return True
        if hasattr(fs, "isdir"):
            return fs.isdir(rest)
        return fs.isdir(rest)

    def exists(self, path: str) -> bool:
        fs, rest = self._resolve(path)
        if fs is None:
            return False
        if not rest:
            return True
        if hasattr(fs, "exists"):
            return fs.exists(rest)
        return fs.exists(rest)

    def scandir(self, path: str) -> list[Any]:
        fs, rest = self._resolve(path)
        if fs is None:
            return []
        if hasattr(fs, "scandir"):
            return fs.scandir(rest)
        raw = fs.ls(rest or "", detail=True)
        return [_FsspecInfoExt(d) for d in raw if d.get("name")]

    def listdir(self, path: str) -> list[str]:
        fs, rest = self._resolve(path)
        if fs is None:
            return []
        if hasattr(fs, "listdir"):
            return fs.listdir(rest)
        return fs.ls(rest or "", detail=False)

    def getinfo(self, path: str, namespaces: Any = None) -> _FsspecInfo:
        fs, rest = self._resolve(path)
        if fs is None:
            raise FileNotFoundError(path)
        if hasattr(fs, "getinfo"):
            return fs.getinfo(rest, namespaces=namespaces)
        info = fs.info(rest or "/")
        return _FsspecInfo(info)

    def getdetails(self, path: str) -> _FsspecInfoExt:
        fs, rest = self._resolve(path)
        if fs is None:
            raise FileNotFoundError(path)
        if hasattr(fs, "getdetails"):
            return fs.getdetails(rest)
        info = fs.info(rest or "/")
        if path.endswith(".zip"):
            info = dict(info)
            info.setdefault("type", "directory")
        return _FsspecInfoExt(info)

    def getsize(self, path: str) -> int:
        fs, rest = self._resolve(path)
        if fs is None:
            raise FileNotFoundError(path)
        if hasattr(fs, "getsize"):
            return fs.getsize(rest)
        return fs.size(rest or "/")

    def getsyspath(self, path: str, allow_none: bool = False) -> str | None:
        fs, rest = self._resolve(path)
        if fs is None:
            if allow_none:
                return None
            raise FileNotFoundError(path)
        if hasattr(fs, "getsyspath"):
            return fs.getsyspath(rest, allow_none=allow_none)
        if isinstance(fs, (LocalFileSystem, _AutoCreateLocalFs)):
            p = os.path.join(fs._root, rest.lstrip("/"))
            if allow_none and not os.path.exists(p):
                return None
            return p
        try:
            proto = getattr(fs, "protocol", None)
            if isinstance(proto, (list, tuple)):
                proto = proto[0] if proto else ""
            if proto and proto != "file":
                return f"{proto}://{rest}"
        except Exception:
            pass
        return f"memory://{rest}"

    def makedirs(self, path: str, recreate: bool = False) -> None:
        fs, rest = self._resolve(path)
        if fs is None:
            return
        if hasattr(fs, "makedirs"):
            fs.makedirs(rest, recreate=recreate)
        else:
            fs.mkdirs(rest, exist_ok=recreate)

    def makedir(self, path: str) -> None:
        fs, rest = self._resolve(path)
        if fs is None:
            return
        if hasattr(fs, "makedir"):
            fs.makedir(rest)
        else:
            fs.mkdir(rest)

    def setbinfile(self, path: str, content: Any) -> None:
        fs, rest = self._resolve(path)
        if fs is None:
            raise FileNotFoundError(path)
        if hasattr(fs, "setbinfile"):
            fs.setbinfile(rest, content)
        else:
            if hasattr(content, "read"):
                data = content.read()
            else:
                data = content
            with fs.open(rest, "wb") as f:
                if isinstance(data, str):
                    data = data.encode("utf-8")
                f.write(data)

    def remove(self, path: str) -> None:
        fs, rest = self._resolve(path)
        if fs is None:
            return
        if hasattr(fs, "remove"):
            fs.remove(rest)
        else:
            fs.rm_file(rest)

    def removetree(self, path: str) -> None:
        fs, rest = self._resolve(path)
        if fs is None:
            return
        if hasattr(fs, "removetree"):
            fs.removetree(rest)
        else:
            fs.rm(rest, recursive=True)

    def copy(self, src: str, dst: str, overwrite: bool = False) -> None:
        fs_src, rest_src = self._resolve(src)
        fs_dst, rest_dst = self._resolve(dst)
        if fs_src is None or fs_dst is None:
            raise FileNotFoundError(src if fs_src is None else dst)
        self._copy_file(fs_src, rest_src, fs_dst, rest_dst, overwrite)

    def copydir(self, src: str, dst: str, overwrite: bool = False, ignore_errors: bool = False) -> None:
        fs_src, rest_src = self._resolve(src)
        fs_dst, rest_dst = self._resolve(dst)
        if fs_src is None or fs_dst is None:
            raise FileNotFoundError(src if fs_src is None else dst)
        self._copy_tree(fs_src, rest_src, fs_dst, rest_dst, overwrite, ignore_errors)

    def move(self, src: str, dst: str, overwrite: bool = False) -> None:
        self.copy(src, dst, overwrite=overwrite)
        with contextlib.suppress(Exception):
            self.remove(src)

    def movedir(self, src: str, dst: str, overwrite: bool = False, ignore_errors: bool = False) -> None:
        self.copydir(src, dst, overwrite=overwrite, ignore_errors=ignore_errors)
        with contextlib.suppress(Exception):
            self.removetree(src)

    @staticmethod
    def _copy_file(fs_src: Any, src: str, fs_dst: Any, dst: str, overwrite: bool) -> None:
        if hasattr(fs_src, "get") and hasattr(fs_dst, "put"):
            fs_src.get(src, dst)
            return
        if overwrite and hasattr(fs_dst, "exists") and fs_dst.exists(dst):
            if hasattr(fs_dst, "remove"):
                fs_dst.remove(dst)
            else:
                fs_dst.rm_file(dst)
        with fs_src.open(src, "rb") as fsrc:
            data = fsrc.read()
        with fs_dst.open(dst, "wb") as fdst:
            fdst.write(data)

    @staticmethod
    def _copy_tree(fs_src: Any, src: str, fs_dst: Any, dst: str, overwrite: bool, ignore_errors: bool) -> None:
        try:
            entries = fs_src.ls(src, detail=True) if hasattr(fs_src, "ls") else []
        except Exception:
            if ignore_errors:
                return
            raise
        if hasattr(fs_dst, "makedirs"):
            fs_dst.makedirs(dst, recreate=True)
        elif hasattr(fs_dst, "mkdirs"):
            fs_dst.mkdirs(dst, exist_ok=True)
        else:
            fs_dst.mkdir(dst, create_parents=True)
        for entry in entries:
            name = (entry.get("name") or "").rstrip("/").rsplit("/", 1)[-1]
            sub_src = f"{src}/{name}" if src else name
            sub_dst = f"{dst}/{name}" if dst else name
            if entry.get("type") == "directory":
                FsspecMountFS._copy_tree(fs_src, sub_src, fs_dst, sub_dst, overwrite, ignore_errors)
            else:
                try:
                    FsspecMountFS._copy_file(fs_src, sub_src, fs_dst, sub_dst, overwrite)
                except Exception:
                    if not ignore_errors:
                        raise

    def __repr__(self) -> str:
        return f"<FsspecMountFS mounts={list(self._mounts.keys())}>"


class FsspecMultiFS:
    """Multi-filesystem composite that chains lookups across sub-filesystems."""

    def __init__(self) -> None:
        self._fs_list: list[tuple[str, Any]] = []

    def add_fs(self, name: str, fs: Any) -> None:
        self._fs_list.append((name, fs))

    def open(self, path: str, mode: str = "rb", **kwargs: Any) -> Any:
        path = path.lstrip("/") or ""
        for _name, fs in self._fs_list:
            try:
                if hasattr(fs, "open"):
                    return fs.open(path, mode, **kwargs)
                return fs._open(path, mode, **kwargs)
            except FileNotFoundError:
                continue
        raise FileNotFoundError(path)

    def isfile(self, path: str) -> bool:
        path = path.lstrip("/") or ""
        return any(hasattr(fs, "isfile") and fs.isfile(path) for _name, fs in self._fs_list)

    def isdir(self, path: str) -> bool:
        path = path.lstrip("/") or ""
        return any(hasattr(fs, "isdir") and fs.isdir(path) for _name, fs in self._fs_list)

    def exists(self, path: str) -> bool:
        path = path.lstrip("/") or ""
        return any(hasattr(fs, "exists") and fs.exists(path) for _name, fs in self._fs_list)

    def ls(self, path: str, detail: bool = False) -> Any:
        path = path.lstrip("/") or ""
        for _name, fs in self._fs_list:
            if fs.isdir(path):
                return fs.ls(path, detail=detail)
        return []

    def info(self, path: str) -> dict[str, Any]:
        path = path.lstrip("/") or ""
        for _name, fs in self._fs_list:
            if fs.exists(path):
                return fs.info(path)
        raise FileNotFoundError(path)

    def getsyspath(self, path: str, allow_none: bool = False) -> str | None:
        path = path.lstrip("/") or ""
        for _name, fs in self._fs_list:
            if hasattr(fs, "getsyspath"):
                r = fs.getsyspath(path, allow_none=True)
                if r:
                    return r
            elif isinstance(fs, (LocalFileSystem, _AutoCreateLocalFs)):
                p = os.path.join(fs._root, path)
                if os.path.exists(p):
                    return p
        if allow_none:
            return None
        raise FileNotFoundError(path)

    def __repr__(self) -> str:
        return f"<FsspecMultiFS subfs={[n for n, _ in self._fs_list]}>"


def _fsspec_abspath(path: str) -> str:
    if not path or path == "/":
        return path
    parts: list[str] = []
    for seg in str(path).replace("\\", "/").split("/"):
        if seg == "..":
            if parts and parts[-1] != "..":
                parts.pop()
        elif seg and seg != ".":
            parts.append(seg)
    return "/" + "/".join(parts)


def _fsspec_dirname(path: str) -> str:
    path = path.rstrip("/")
    if "/" not in path:
        return ""
    if path == "":
        return "/"
    return path.rsplit("/", 1)[0] or "/"


def _fsspec_join(*args: str) -> str:
    result = ""
    for a in args:
        a = str(a).strip("/")
        if a:
            result += "/" + a
    return result or "/"
