"""Virtual filesystem tools: path normalisation, file I/O, zip handling, and format conversion."""

from __future__ import annotations

import email.generator
import hashlib
import os
import re
import tempfile
import zipfile
from tempfile import NamedTemporaryFile
from typing import Any, Callable, Optional, Union

from django.conf import settings
from django.core.files.storage import default_storage
from fs.osfs import OSFS


def norm_path(url: Optional[str]) -> str:
    """Normalize a path-like string by resolving ``..`` and ``.`` segments.

    The function also handles URL-encoded spaces and ``://``-style protocol
    prefixes so that they are not corrupted during splitting/joining.

    Args:
        url: The raw path or URL string.  May be *None* or empty.

    Returns:
        The normalized path.  An empty input yields an empty string.
        A path that normalizes to the root yields ``"/"``.
    """
    if not url:
        return ""
    # Protect protocol prefixes and spaces during split/join.
    url2 = url.replace(" ", "%20").replace("://", "###").replace("\\", "/")
    if "." not in url2:
        return url2.replace("###", "://").replace("%20", " ")

    ldest: list[str] = []
    for segment in url2.split("/"):
        if segment == "..":
            if ldest:
                ldest.pop()
        elif segment != ".":
            ldest.append(segment)

    if not ldest:
        return ""
    result = "/".join(ldest)
    if result == "":
        return "/"
    return result.replace("###", "://").replace("%20", " ")


def open_file(filename: str, mode: str, for_vfs: bool = False) -> Any:
    """Open a file from the local filesystem or the virtual filesystem.

    Args:
        filename: Path to the file.
        mode: I/O mode (e.g. ``"r"``, ``"wb"``).
        for_vfs: If *True*, open through Django's default storage VFS.

    Returns:
        A file-like object.

    Raises:
        OSError: If the file cannot be opened.
    """
    try:
        if for_vfs:
            return default_storage.fs.open(filename, mode)
        return open(filename, mode)
    except Exception as e:
        raise OSError(f"Failed to open file '{filename}': {e}") from e


def open_and_create_dir(filename: str, mode: str, for_vfs: bool = False) -> Any:
    """Open a file, creating intermediate directories as needed.

    Args:
        filename: Path to the file.
        mode: I/O mode (e.g. ``"r"``, ``"wb"``).
        for_vfs: If *True*, create directories through Django's VFS.

    Returns:
        A file-like object.

    Raises:
        OSError: If the directory cannot be created or the file cannot be opened.
    """
    try:
        dirname = os.path.dirname(filename)
        if for_vfs:
            if not default_storage.fs.exists(dirname):
                default_storage.fs.makedirs(dirname)
        else:
            if not os.path.exists(dirname):
                os.makedirs(dirname)
        return open_file(filename, mode, for_vfs)
    except Exception as e:
        raise OSError(
            f"Failed to create directory or open file '{filename}': {e}"
        ) from e


def get_unique_filename(
    base_name: Optional[str] = None, ext: Optional[str] = None
) -> str:
    """Generate a unique filename using an email-style MIME boundary.

    Args:
        base_name: Optional descriptive name embedded in the result.
        ext: Optional file extension (without leading dot).

    Returns:
        A unique filename string suitable for temporary files.
    """
    boundary: str = email.generator._make_boundary()
    if base_name:
        boundary += f"_{base_name}"
    if ext:
        boundary += f".{ext}"
    return boundary


def get_temp_filename(
    base_name: Optional[str] = None,
    ext: Optional[str] = None,
    for_vfs: bool = False,
) -> str:
    """Return a full path for a temporary file.

    Args:
        base_name: Optional descriptive name.
        ext: Optional file extension (without leading dot).
        for_vfs: If *True*, place the file under the VFS ``/temp/`` prefix.

    Returns:
        An absolute path (local or VFS) to a unique temporary file.
    """
    filename = get_unique_filename(base_name, ext)
    if for_vfs:
        return f"/temp/{filename}"
    return os.path.join(settings.TEMP_PATH, filename)


def delete_from_zip(zip_name: str, del_file_names: list[str]) -> bool:
    """Delete entries from a zip archive.

    Creates a temporary zip, copies all entries whose (lowercased) names are
    not in *del_file_names*, and then atomically replaces the original.

    Args:
        zip_name: Path to the source zip archive.
        del_file_names: List of file names to remove (case-insensitive).

    Returns:
        *True* on success.

    Raises:
        OSError: If the zip cannot be read, written, or replaced.
    """
    del_file_names = [name.lower() for name in del_file_names]
    tmpname = get_temp_filename()

    try:
        with zipfile.ZipFile(zip_name, "r") as zin:
            with zipfile.ZipFile(tmpname, "w", zipfile.ZIP_STORED) as zout:
                for item in zin.infolist():
                    if item.filename.lower() not in del_file_names:
                        zout.writestr(item, zin.read(item.filename))

        os.remove(zip_name)
        os.rename(tmpname, zip_name)
        return True
    except Exception as e:
        raise OSError(f"Failed to delete files from zip '{zip_name}': {e}") from e


def _clear_content(data: bytes) -> bytes:
    """Strip all whitespace characters from binary data.

    Useful for comparing text-based file contents where formatting
    differences (spaces, newlines, tabs) should be ignored.
    """
    return (
        data.replace(b" ", b"")
        .replace(b"\n", b"")
        .replace(b"\t", b"")
        .replace(b"\r", b"")
    )


def _cmp_txt_str_content(data1: bytes, data2: bytes) -> bool:
    """Return *True* if two byte strings are identical after stripping whitespace."""
    return _clear_content(data1) == _clear_content(data2)


def extractall(
    zip_file: zipfile.ZipFile,
    path: Optional[str] = None,
    members: Optional[list[str]] = None,
    pwd: Optional[str] = None,
    exclude: Optional[list[str]] = None,
    backup_zip: Optional[zipfile.ZipFile] = None,
    backup_exts: Optional[list[str]] = None,
    only_path: Optional[str] = None,
) -> None:
    """Extract files from a zip archive, with optional backup of overwritten files.

    Args:
        zip_file: An open :class:`zipfile.ZipFile` instance.
        path: Destination directory.  Created if missing.
        members: List of member names to extract (defaults to all).
        pwd: Password for encrypted members.
        exclude: List of regex patterns; matching entries are skipped.
        backup_zip: If provided, an open writable :class:`~zipfile.ZipFile`
            where the *previous* version of a file is stored before it is
            overwritten.
        backup_exts: If provided, only files whose extension is in this
            list are eligible for backup.
        only_path: If provided, only members whose name starts with this
            prefix are extracted.
    """
    if path is None:
        path = ""
    if members is None:
        members = zip_file.namelist()

    for zipinfo_name in members:
        if only_path and not zipinfo_name.startswith(only_path):
            continue

        if zipinfo_name.endswith(("/", "\\")):
            os.makedirs(os.path.join(path, zipinfo_name), exist_ok=True)
        else:
            if exclude and any(
                re.match(pattern, zipinfo_name, re.I) for pattern in exclude
            ):
                continue

            out_name = os.path.join(path, zipinfo_name)
            if backup_zip is not None and (
                not backup_exts or zipinfo_name.rsplit(".", 1)[-1] in backup_exts
            ):
                if os.path.exists(out_name):
                    new_data = zip_file.read(zipinfo_name, pwd)
                    with open(out_name, "rb") as f:
                        old_data = f.read()
                    if not _cmp_txt_str_content(new_data, old_data):
                        backup_zip.writestr(zipinfo_name, old_data)

            zip_file.extract(zipinfo_name, path, pwd)


class ZipWriter:
    """Helper to create zip files with optional SHA-256 checksums and exclusions."""

    def __init__(
        self,
        filename: str,
        basepath: str = "",
        exclude: Optional[list[str]] = None,
        sha256: bool = False,
    ) -> None:
        """Initialise the writer.

        Args:
            filename: Path of the output zip file.
            basepath: Common root path that will be stripped from entry names.
            exclude: List of regex patterns; files whose name matches any
                pattern are skipped.
            sha256: If *True*, record SHA-256 hashes of every entry.
        """
        self.filename = filename
        self.basepath = basepath.rstrip("/\\")
        self.base_len = len(self.basepath)
        self.zip_file = zipfile.ZipFile(
            filename, "w", zipfile.ZIP_BZIP2, compresslevel=9
        )
        self.exclude = exclude or []
        self.sha256_tab: Optional[list[tuple[str, str, int]]] = [] if sha256 else None

    def close(self) -> None:
        """Finalise and close the underlying zip file."""
        self.zip_file.close()

    def _sha256_gen(self, file_name: str, data: bytes) -> None:
        """Record a SHA-256 hash for *data* if checksum tracking is enabled."""
        if self.sha256_tab is not None:
            sha256 = hashlib.sha256(data).hexdigest()
            self.sha256_tab.append((file_name, sha256, len(data)))

    def _strip_base(self, file_name: str) -> str:
        """Return *file_name* relative to :attr:`basepath`.

        If the file is not inside the basepath or starts exactly at it the
        path is returned as-is.
        """
        if self.base_len and file_name.startswith(self.basepath):
            # Skip the basepath directory and the following separator.
            return file_name[self.base_len :].lstrip("/\\")
        return file_name

    def write(
        self,
        file_name: str,
        name_in_zip: Optional[str] = None,
        base_path_in_zip: Optional[str] = None,
    ) -> None:
        """Add a file from the local filesystem to the archive.

        Args:
            file_name: Path on disk.
            name_in_zip: Explicit archive name (overrides automatic naming).
            base_path_in_zip: Prepended to the relative path derived from
                :attr:`basepath`.
        """
        if any(re.match(pattern, file_name, re.I) for pattern in self.exclude):
            return

        try:
            with open(file_name, "rb") as f:
                data = f.read()
        except OSError:
            # Skip files that cannot be read (permissions, etc.).
            return

        if name_in_zip:
            self.writestr(name_in_zip, data)
        elif base_path_in_zip is not None:
            self.writestr(
                base_path_in_zip.rstrip("/") + "/" + self._strip_base(file_name),
                data,
            )
        else:
            self.writestr(self._strip_base(file_name), data)

    def writestr(self, path: str, data: bytes) -> None:
        """Write raw *data* as a member named *path* inside the archive."""
        self._sha256_gen(path, data)
        self.zip_file.writestr(path, data)

    def to_zip(self, file: str, base_path_in_zip: Optional[str] = None) -> None:
        """Add *file* (or recursively add a directory) to the archive.

        Args:
            file: Path to a file or directory on the local filesystem.
            base_path_in_zip: Optional prefix prepended to archive member names.
        """
        if os.path.isfile(file):
            self.write(file, base_path_in_zip=base_path_in_zip)
        else:
            self.add_folder_to_zip(file, base_path_in_zip=base_path_in_zip)

    def add_folder_to_zip(
        self, folder: str, base_path_in_zip: Optional[str] = None
    ) -> None:
        """Recursively add *folder* contents to the archive."""
        try:
            entries = os.listdir(folder)
        except OSError:
            return
        for name in entries:
            full_path = os.path.join(folder, name)
            if os.path.isfile(full_path):
                self.write(full_path, base_path_in_zip=base_path_in_zip)
            elif os.path.isdir(full_path):
                self.add_folder_to_zip(full_path, base_path_in_zip=base_path_in_zip)


def automount(path: str) -> str:
    """Auto-mount a zip file as a virtual filesystem if *path* points inside one.

    When *path* references a ``.zip`` archive (e.g.
    ``/data/archive.zip/some/file.txt``), the function looks up the
    real filesystem path of the zip, mounts it via :class:`fs.osfs.OSFS`,
    and returns the unchanged *path* so subsequent VFS operations resolve
    transparently.

    Args:
        path: A VFS path that may reference a zip-backed location.

    Returns:
        The unchanged *path* argument.
    """
    lower = path.lower()
    if lower.endswith(".zip") or ".zip/" in lower:
        zip_end = lower.find(".zip") + 4
        zip_path = path[:zip_end]
        syspath = default_storage.fs.getsyspath(zip_path, allow_none=True)
        if syspath:
            zip_name = f"zip://{syspath}"
            try:
                default_storage.fs.add_fs(zip_path[1:], OSFS(zip_name))
            except Exception:
                # If mounting fails (e.g. not a valid zip), silently ignore.
                pass
    return path


def convert_file(
    filename_or_stream_in: Union[str, Any],
    filename_or_stream_out: Union[str, Any],
    input_format: Optional[str] = None,
    output_format: Optional[str] = None,
    for_vfs_input: bool = True,
    for_vfs_output: bool = True,
) -> bool:
    """Convert a document from one format to another.

    Supported **input** formats (auto-detected from file extension or
    specified explicitly):

    * ``"imd"``  – indented markdown (processed via
      :class:`~pytigon_lib.schindent.indent_markdown.IndentMarkdownProcessor`)
    * ``"md"``   – plain Markdown
    * ``"ihtml"`` – indented HTML
    * ``"spdf"`` – serialised PDF (replayed via
      :class:`~pytigon_lib.schhtml.pdfdc.PdfDc`)
    * anything else is treated as raw HTML text

    Supported **output** formats:

    * ``"html"``  – HTML (written directly as UTF-8)
    * ``"pdf"``   – PDF via :class:`~pytigon_lib.schhtml.pdfdc.PdfDc`
    * ``"xpdf"``  – same as PDF but attaches subject metadata
    * ``"spdf"``  – serialised PDF (for later replay)
    * ``"docx"``  – DOCX via :class:`~pytigon_lib.schhtml.docxdc.DocxDc`
    * ``"xlsx"``  – XLSX via :class:`~pytigon_lib.schhtml.xlsxdc.XlsxDc`

    Args:
        filename_or_stream_in: Source file path (local or VFS) or an
            open readable stream.
        filename_or_stream_out: Destination file path or an open writable
            stream.
        input_format: Override auto-detection; one of the keys listed above.
        output_format: Override auto-detection; one of the keys listed above.
        for_vfs_input: If *True* (default), open *filename_or_stream_in*
            through the VFS.
        for_vfs_output: If *True* (default), open *filename_or_stream_out*
            through the VFS.

    Returns:
        *True* on success.

    Raises:
        ValueError: If the *output_format* is not recognised.
        OSError: If any file or stream operation fails.
    """
    # Lazy imports to avoid circular dependencies at module level.
    from pytigon_lib.schhtml.basedc import BaseDc  # noqa: F811
    from pytigon_lib.schhtml.pdfdc import PdfDc
    from pytigon_lib.schhtml.docxdc import DocxDc
    from pytigon_lib.schhtml.xlsxdc import XlsxDc
    from pytigon_lib.schhtml.htmlviewer import HtmlViewerParser
    from pytigon_lib.schindent.indent_style import ihtml_to_html_base
    from pytigon_lib.schindent.indent_markdown import markdown_to_html

    # Recognised output formats that require a dc (document-converter) object.
    _DC_FORMATS = frozenset({"pdf", "xpdf", "spdf", "docx", "xlsx"})

    try:
        # ---- open input ----
        if isinstance(filename_or_stream_in, str):
            fin: Any = open_file(
                automount(filename_or_stream_in),
                "rt" if for_vfs_input else "rb",
                for_vfs_input,
            )
            input_format = (
                input_format or filename_or_stream_in.rsplit(".", 1)[-1].lower()
            )
        else:
            fin = filename_or_stream_in

        # ---- open output ----
        if isinstance(filename_or_stream_out, str):
            fout: Any = open_file(
                automount(filename_or_stream_out), "wb", for_vfs_output
            )
            output_format = (
                output_format or filename_or_stream_out.rsplit(".", 1)[-1].lower()
            )
        else:
            fout = filename_or_stream_out

        # ---- read / convert input to HTML buffer ----
        if input_format == "imd":
            from pytigon_lib.schindent.indent_markdown import (
                IndentMarkdownProcessor,
            )

            processor = IndentMarkdownProcessor(output_format="html")
            buf: Optional[str] = processor.convert(fin.read())
        elif input_format == "md":
            buf = markdown_to_html(fin.read())
        elif input_format == "ihtml":
            buf = ihtml_to_html_base(None, input_str=fin.read())
        elif input_format == "spdf":
            buf = None
        else:
            buf = fin.read()

        # ---- early return for HTML output ----
        if output_format == "html":
            if buf is not None:
                fout.write(buf.encode("utf-8"))
            return True

        # ---- determine document converter ----
        dc: Any = None

        if output_format in ("pdf", "xpdf"):

            def notify_callback_pdf(event_name: str, data: dict[str, Any]) -> None:
                if event_name == "end" and buf:
                    dc_obj = data["dc"]
                    dc_obj.surf.pdf.set_subject(buf)

            dc = PdfDc(
                output_stream=fout,
                notify_callback=(
                    notify_callback_pdf if output_format == "xpdf" else None
                ),
            )
            dc.set_paging(True)

        elif output_format == "spdf":

            def notify_callback_spdf(event_name: str, data: dict[str, Any]) -> None:
                if event_name == "end":
                    dc_obj: Any = data["dc"]
                    if dc_obj.output_name:
                        dc_obj.save(dc_obj.output_name)
                    else:
                        with NamedTemporaryFile(delete=False) as temp_file:
                            dc_obj.save(temp_file.name)
                            with open(temp_file.name, "rb") as f:
                                dc_obj.output_stream.write(f.read())

            dc = PdfDc(
                output_stream=fout,
                calc_only=True,
                width=595,
                height=842,
                notify_callback=notify_callback_spdf,
                record=True,
            )
            dc.set_paging(True)

        elif output_format == "docx":
            dc = DocxDc(output_stream=fout)
        elif output_format == "xlsx":
            dc = XlsxDc(output_stream=fout)
        else:
            raise ValueError(
                f"Unsupported output format: '{output_format}'. "
                f"Supported formats: html, pdf, xpdf, spdf, docx, xlsx."
            )

        # ---- render ----
        p = HtmlViewerParser(
            dc=dc,
            calc_only=False,
            init_css_str="@wiki.icss",
            css_type=1,
            use_tag_maps=True,
        )
        if input_format == "spdf":
            dc.load(filename_or_stream_in)
            dc.play()
        else:
            if buf is not None:
                p.feed(buf)
        p.close()

        return True

    except ValueError:
        # Re-raise known validation errors unchanged.
        raise
    except Exception as e:
        raise OSError(f"Failed to convert file: {e}") from e
    finally:
        if isinstance(filename_or_stream_in, str):
            try:
                fin.close()
            except Exception:
                pass
        if isinstance(filename_or_stream_out, str):
            try:
                fout.close()
            except Exception:
                pass
