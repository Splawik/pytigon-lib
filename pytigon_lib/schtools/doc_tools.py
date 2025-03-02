import tempfile
import shutil
import os


def soffice_convert(in_file_path, out_file_path, format):
    """
    Convert file using LibreOffice/OpenOffice.

    :param in_file_path: Source file path
    :param out_file_path: Destination file path
    :param format: format to convert to. Examples: "pdf", "odt", "docx", "ods", "xlsx", "txt", "csv", "html"
    :return: None
    """
    tmp_path = tempfile.gettempdir()
    cmd = "soffice --headless --convert-to %s %s --outdir %s" % (
        format,
        in_file_path,
        tmp_path,
    )
    os.system(cmd)
    _, ext = os.path.splitext(in_file_path)
    f = format.split(":")[0]
    shutil.move(
        os.path.join(tmp_path, os.path.basename(in_file_path).replace(ext, "." + f)),
        out_file_path,
    )
