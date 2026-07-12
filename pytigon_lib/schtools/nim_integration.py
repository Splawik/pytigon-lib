"""Nim compiler download, installation, and zigcc wrapper setup.

Automates fetching the Nim toolchain, extracting it, configuring
nim.cfg to use a zig-based C compiler wrapper, and compiling the
zigcc helper binary.
"""

import lzma
import logging
import os
import stat
import tarfile
import tempfile
import zipfile

import httpx

_logger = logging.getLogger(__name__)

from pytigon_lib.schtools.process import run


def _is_safe_tar_member(member: tarfile.TarInfo, target_path: str) -> bool:
    """Prevent path traversal in tar extraction."""
    resolved = os.path.realpath(os.path.join(target_path, member.name))
    target_real = os.path.realpath(target_path)
    return os.path.commonpath([resolved, target_real]) == target_real


def _is_safe_zip_member(member_name: str, target_path: str) -> bool:
    """Prevent path traversal in zip extraction."""
    resolved = os.path.realpath(os.path.join(target_path, member_name))
    target_real = os.path.realpath(target_path)
    return os.path.commonpath([resolved, target_real]) == target_real

# C source for the zigcc wrapper: forwards all arguments to 'ptig zig cc'
ZIG_CC_C = """
#include <string.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argi, char **argv)
{
    char **buf = (char **)malloc(sizeof(char *) * (argi + 3));
    buf[0] = "ptig";
    buf[1] = "zig";
    buf[2] = "cc";
    memcpy(buf + 3, argv + 1, sizeof(char *) * (argi - 1));
    buf[argi + 2] = 0;
    execvp("ptig", buf);
}
"""

NIM_DOWNLOAD_PATH = (
    "https://nim-lang.org/download/nim-2.0.4_x64.zip"
    if os.name == "nt"
    else "https://nim-lang.org/download/nim-2.0.4-linux_x64.tar.xz"
)


def install_nim(data_path: str) -> None:
    """Download and install the Nim compiler into *data_path*/prg/.

    On Linux, the downloaded .tar.xz is decompressed via lzma then tar.
    On Windows, a .zip is extracted directly. After extraction, the
    nim.cfg is patched to use the zigcc wrapper and the wrapper binary
    is compiled.

    Args:
        data_path: Root data directory (e.g. ``settings.DATA_PATH``).
    """
    temp_dir = tempfile.gettempdir()
    try:
        r = httpx.get(NIM_DOWNLOAD_PATH, follow_redirects=True)
        r.raise_for_status()
    except httpx.HTTPError as e:
        _logger.warning("Failed to download Nim: %s", e)
        return

    prg_path = os.path.join(data_path, "prg")
    os.makedirs(prg_path, exist_ok=True)

    if os.name == "nt":
        nim_zip = os.path.join(temp_dir, "nim.zip")
        with open(nim_zip, "wb") as f:
            f.write(r.content)

        with zipfile.ZipFile(nim_zip) as f:
            for member in f.infolist():
                if _is_safe_zip_member(member.filename, prg_path):
                    f.extract(member, prg_path)
                else:
                    _logger.warning("Skipping unsafe zip entry: %s", member.filename)
    else:
        nim_tar_xz = os.path.join(temp_dir, "nim.tar.xz")
        nim_tar = os.path.join(temp_dir, "nim.tar")
        with open(nim_tar_xz, "wb") as f:
            f.write(r.content)

        with lzma.open(nim_tar_xz) as f:
            buf = f.read()
        with open(nim_tar, "wb") as f:
            f.write(buf)

        with tarfile.open(nim_tar, "r") as tar:
            for member in tar.getmembers():
                if member.isdir():
                    os.makedirs(os.path.join(prg_path, member.name), exist_ok=True)
                elif _is_safe_tar_member(member, prg_path):
                    tar.extract(member, prg_path)
                else:
                    _logger.warning("Skipping unsafe tar entry: %s", member.name)

    nim_path = get_nim_path(data_path)
    if not nim_path:
        _logger.error("Nim installation path not found after extraction.")
        return

    # Patch nim.cfg to use zigcc as the C compiler
    nim_cfg_path = os.path.join(nim_path, "config", "nim.cfg")
    try:
        with open(nim_cfg_path) as f:
            buf = f.read()
            buf = buf.replace(
                "cc = gcc",
                "cc = clang\nclang.exe = zigcc\nclang.linkerexe = zigcc\n",
            )
        with open(nim_cfg_path, "w") as f:
            f.write(buf)
    except OSError as e:
        _logger.error("Failed to update nim.cfg: %s", e)
        return

    # Compile the zigcc wrapper
    zigcc_bin = os.path.join(
        nim_path, "bin", "zigcc.exe" if os.name == "nt" else "zigcc"
    )
    zigcc_c = os.path.join(temp_dir, "zigcc.c")
    try:
        with open(zigcc_c, "w") as f:
            f.write(ZIG_CC_C)
    except OSError as e:
        _logger.error("Failed to write zigcc.c: %s", e)
        return

    exit_code, output_tab, err_tab = run(
        ["ptig", "zig", "cc", "-o", zigcc_bin, zigcc_c], env=os.environ
    )
    if err_tab:
        _logger.error("zigcc build output: %s", err_tab)

    # Ensure the wrapper is executable on Unix
    if os.name != "nt":
        try:
            st = os.stat(zigcc_bin)
            os.chmod(zigcc_bin, st.st_mode | stat.S_IEXEC)
        except OSError as e:
            _logger.error("Failed to set executable permissions on zigcc: %s", e)


def get_nim_path(data_path: str) -> str | None:
    """Find the Nim installation directory under *data_path*/prg/.

    Args:
        data_path: Root data directory.

    Returns:
        The path to the ``nim-*`` directory, or None if not found.
    """
    prg_path = os.path.join(data_path, "prg")
    if not os.path.exists(prg_path):
        return None
    for item in os.listdir(prg_path):
        if item.startswith("nim-"):
            return os.path.join(prg_path, item)
    return None


def install_if_not_exists(data_path: str) -> str | None:
    """Ensure Nim is installed, downloading it if necessary.

    Args:
        data_path: Root data directory.

    Returns:
        The Nim installation path, or None if installation failed.
    """
    nim_path = get_nim_path(data_path)
    if nim_path:
        return nim_path
    install_nim(data_path)
    return get_nim_path(data_path)
