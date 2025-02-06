import re
import os
import tempfile
import email.generator
import zipfile
import hashlib
from tempfile import NamedTemporaryFile
from django.core.files.storage import default_storage
from django.conf import settings
from pytigon_lib.schdjangoext.tools import gettempdir


def norm_path(url):
    """Normalize URL by removing redundant slashes and resolving '..' and '.'."""
    ldest = []
    if url == "" or url == None:
        return ""
    url2 = url.replace(" ", "%20").replace("://", "###").replace("\\", "/")
    if not "." in url2:
        return url2.replace("###", "://").replace("%20", " ")
    lsource = url2.split("/")
    for l in lsource:
        if l == "..":
            ldest.pop()
        else:
            if l != ".":
                ldest.append(l)
    ret = None
    for l in ldest:
        if ret == None:
            ret = l
        else:
            ret = ret + "/" + l
    if ret != None:
        if ret == "":
            return "/"
        else:
            return ret.replace("###", "://").replace("%20", " ")
    else:
        return ""


def open_file(filename, mode, for_vfs=False):
    """Open a file, either from the filesystem or from a virtual filesystem."""
    try:
        if for_vfs:
            return default_storage.fs.open(filename, mode)
        return open(filename, mode)
    except Exception as e:
        raise IOError(f"Failed to open file {filename}: {e}")


def open_and_create_dir(filename, mode, for_vfs=False):
    """Open a file, creating the directory if it doesn't exist."""
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
        raise IOError(f"Failed to create directory or open file {filename}: {e}")


def get_unique_filename(base_name=None, ext=None):
    """Generate a unique filename using a boundary string."""
    boundary = email.generator._make_boundary()
    if base_name:
        boundary += f"_{base_name}"
    if ext:
        boundary += f".{ext}"
    return boundary


def get_temp_filename(base_name=None, ext=None, for_vfs=False):
    """Get a temporary filename, optionally with a base name and extension."""
    filename = get_unique_filename(base_name, ext)
    if for_vfs:
        return f"/temp/{filename}"
    return os.path.join(settings.TEMP_PATH, filename)


def delete_from_zip(zip_name, del_file_names):
    """Delete files from a zip archive."""
    del_file_names = [name.lower() for name in del_file_names]
    tmpname = get_temp_filename()

    try:
        with (
            zipfile.ZipFile(zip_name, "r") as zin,
            zipfile.ZipFile(tmpname, "w", zipfile.ZIP_STORED) as zout,
        ):
            for item in zin.infolist():
                if item.filename.lower() not in del_file_names:
                    zout.writestr(item, zin.read(item.filename))

        os.remove(zip_name)
        os.rename(tmpname, zip_name)
        return 1
    except Exception as e:
        raise IOError(f"Failed to delete files from zip {zip_name}: {e}")


def _clear_content(data):
    """Remove whitespace and newlines from binary data."""
    return (
        data.replace(b" ", b"")
        .replace(b"\n", b"")
        .replace(b"\t", b"")
        .replace(b"\r", b"")
    )


def _cmp_txt_str_content(data1, data2):
    """Compare two binary strings after clearing whitespace."""
    return _clear_content(data1) == _clear_content(data2)


def extractall(
    zip_file,
    path=None,
    members=None,
    pwd=None,
    exclude=None,
    backup_zip=None,
    backup_exts=None,
    only_path=None,
):
    """Extract files from a zip archive, optionally backing up overwritten files."""
    if members is None:
        members = zip_file.namelist()

    for zipinfo in members:
        if only_path and not zipinfo.startswith(only_path):
            continue

        if zipinfo.endswith(("/", "\\")):
            os.makedirs(os.path.join(path, zipinfo), exist_ok=True)
        else:
            if exclude and any(re.match(pattern, zipinfo, re.I) for pattern in exclude):
                continue

            out_name = os.path.join(path, zipinfo)
            if backup_zip and (
                not backup_exts or zipinfo.split(".")[-1] in backup_exts
            ):
                if os.path.exists(out_name):
                    new_data = zip_file.read(zipinfo, pwd)
                    with open(out_name, "rb") as f:
                        old_data = f.read()
                    if not _cmp_txt_str_content(new_data, old_data):
                        backup_zip.writestr(zipinfo, old_data)

            zip_file.extract(zipinfo, path, pwd)


class ZipWriter:
    """Helper class to create zip files."""

    def __init__(self, filename, basepath="", exclude=None, sha256=False):
        self.filename = filename
        self.basepath = basepath
        self.base_len = len(self.basepath)
        self.zip_file = zipfile.ZipFile(
            filename, "w", zipfile.ZIP_BZIP2, compresslevel=9
        )
        self.exclude = exclude or []
        self.sha256_tab = [] if sha256 else None

    def close(self):
        """Close the zip file."""
        self.zip_file.close()

    def _sha256_gen(self, file_name, data):
        """Generate SHA256 hash for the file content."""
        if self.sha256_tab is not None:
            sha256 = hashlib.sha256(data).hexdigest()
            self.sha256_tab.append((file_name, sha256, len(data)))

    def write(self, file_name, name_in_zip=None, base_path_in_zip=None):
        """Write a file to the zip archive."""
        if any(re.match(pattern, file_name, re.I) for pattern in self.exclude):
            return

        with open(file_name, "rb") as f:
            data = f.read()
            if name_in_zip:
                self.writestr(name_in_zip, data)
            elif base_path_in_zip:
                self.writestr(base_path_in_zip + file_name[self.base_len + 1 :], data)
            else:
                self.writestr(file_name[self.base_len + 1 :], data)

    def writestr(self, path, data):
        """Write data to a file in the zip archive."""
        self._sha256_gen(path, data)
        self.zip_file.writestr(path, data)

    def to_zip(self, file, base_path_in_zip=None):
        """Add a file or folder to the zip archive."""
        if os.path.isfile(file):
            self.write(file, base_path_in_zip=base_path_in_zip)
        else:
            self.add_folder_to_zip(file, base_path_in_zip=base_path_in_zip)

    def add_folder_to_zip(self, folder, base_path_in_zip=None):
        """Recursively add a folder to the zip archive."""
        for file in os.listdir(folder):
            full_path = os.path.join(folder, file)
            if os.path.isfile(full_path):
                self.write(full_path, base_path_in_zip=base_path_in_zip)
            elif os.path.isdir(full_path):
                self.add_folder_to_zip(full_path, base_path_in_zip=base_path_in_zip)


def automount(path):
    """Mount a zip file as a virtual filesystem if the path points to a zip file."""
    if path.lower().endswith(".zip") or ".zip/" in path.lower():
        zip_path = path[: path.lower().find(".zip") + 4]
        syspath = default_storage.fs.getsyspath(zip_path, allow_none=True)
        if syspath:
            zip_name = f"zip://{syspath}"
            default_storage.fs.add_fs(zip_path[1:], OSFS(zip_name))
    return path


def convert_file(
    filename_or_stream_in,
    filename_or_stream_out,
    input_format=None,
    output_format=None,
    for_vfs_input=True,
    for_vfs_output=True,
):
    """Convert a file from one format to another."""
    from pytigon_lib.schhtml.basedc import BaseDc
    from pytigon_lib.schhtml.pdfdc import PdfDc
    from pytigon_lib.schhtml.docxdc import DocxDc
    from pytigon_lib.schhtml.xlsxdc import XlsxDc
    from pytigon_lib.schhtml.htmlviewer import HtmlViewerParser
    from pytigon_lib.schindent.indent_style import ihtml_to_html_base
    from pytigon_lib.schindent.indent_markdown import markdown_to_html

    try:
        if isinstance(filename_or_stream_in, str):
            fin = open_file(
                automount(filename_or_stream_in),
                "rt" if for_vfs_input else "rb",
                for_vfs_input,
            )
            input_format = input_format or filename_or_stream_in.split(".")[-1].lower()
        else:
            fin = filename_or_stream_in

        if isinstance(filename_or_stream_out, str):
            fout = open_file(automount(filename_or_stream_out), "wb", for_vfs_output)
            output_format = (
                output_format or filename_or_stream_out.split(".")[-1].lower()
            )
        else:
            fout = filename_or_stream_out

        if input_format == "imd":
            from pytigon_lib.schindent.indent_markdown import IndentMarkdownProcessor

            processor = IndentMarkdownProcessor(output_format="html")
            buf = processor.convert(fin.read())
        elif input_format == "md":
            buf = markdown_to_html(fin.read())
        elif input_format == "ihtml":
            buf = ihtml_to_html_base(None, input_str=fin.read())
        elif input_format == "spdf":
            buf = None
        else:
            buf = fin.read()

        if output_format == "html":
            fout.write(buf.encode("utf-8"))
            return True

        if output_format in ("pdf", "xpdf"):

            def notify_callback(event_name, data):
                if event_name == "end":
                    dc = data["dc"]
                    dc.surf.pdf.set_subject(buf)

            dc = PdfDc(
                output_stream=fout,
                notify_callback=notify_callback if output_format == "xpdf" else None,
            )
            dc.set_paging(True)
        elif output_format == "spdf":

            def notify_callback(event_name, data):
                if event_name == "end":
                    dc = data["dc"]
                    if dc.output_name:
                        dc.save(dc.output_name)
                    else:
                        with NamedTemporaryFile(delete=False) as temp_file:
                            dc.save(temp_file.name)
                            with open(temp_file.name, "rb") as f:
                                dc.output_stream.write(f.read())

            dc = PdfDc(
                output_stream=fout,
                calc_only=True,
                width=595,
                height=842,
                notify_callback=notify_callback,
                record=True,
            )
            dc.set_paging(True)
        elif output_format == "docx":
            dc = DocxDc(output_stream=fout)
        elif output_format == "xlsx":
            dc = XlsxDc(output_stream=fout)

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
            p.feed(buf)
        p.close()

        if isinstance(filename_or_stream_in, str):
            fin.close()
        if isinstance(filename_or_stream_out, str):
            fout.close()
        return True
    except Exception as e:
        raise IOError(f"Failed to convert file: {e}")
