import logging
import os
import shutil
import subprocess
import tempfile

logger = logging.getLogger(__name__)


def soffice_convert(in_file_path, out_file_path, format):
    """
    Convert a file using LibreOffice/OpenOffice in headless mode.

    Uses subprocess.run for safe execution with proper error handling.
    The converted file is first written to a temporary directory and then
    moved to the target location.

    Args:
        in_file_path (str): Path to the source file.
        out_file_path (str): Path where the converted file should be saved.
        format (str): Target format, e.g. "pdf", "odt", "docx", "ods",
                      "xlsx", "txt", "csv", "html". May include a filter
                      prefix separated by colon (e.g. "pdf:writer_pdf_Export").

    Raises:
        FileNotFoundError: If the source file does not exist.
        subprocess.CalledProcessError: If the soffice command fails.
        RuntimeError: If the converted file is not found at the expected location.

    Returns:
        None
    """
    if not os.path.isfile(in_file_path):
        raise FileNotFoundError(f"Source file not found: {in_file_path}")

    tmp_path = tempfile.gettempdir()
    cmd = [
        "soffice",
        "--headless",
        "--convert-to",
        format,
        "--outdir",
        tmp_path,
        in_file_path,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, cmd, output=result.stdout, stderr=result.stderr
            )
    except FileNotFoundError:
        raise RuntimeError(
            "soffice command not found. Please install LibreOffice or OpenOffice."
        )

    _, ext = os.path.splitext(in_file_path)
    filter_suffix = format.split(":")[0]
    converted_name = os.path.basename(in_file_path).replace(ext, "." + filter_suffix)
    converted_path = os.path.join(tmp_path, converted_name)

    if not os.path.isfile(converted_path):
        raise RuntimeError(
            f"Converted file not found at expected location: {converted_path}. "
            f"soffice stderr: {result.stderr}"
        )

    shutil.move(converted_path, out_file_path)
