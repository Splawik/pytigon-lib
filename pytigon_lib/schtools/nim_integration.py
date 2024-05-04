import lzma
import httpx
import tarfile
import zipfile
import os
import tempfile
import stat

from pytigon_lib.schtools.process import run

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

if os.name == "nt":
    NIM_DOWNLOAD_PATH = "https://nim-lang.org/download/nim-2.0.4_x64.zip"
else:
    NIM_DOWNLOAD_PATH = "https://nim-lang.org/download/nim-2.0.4-linux_x64.tar.xz"


def install_nim(data_path):
    temp_dir = tempfile.gettempdir()
    r = httpx.get(NIM_DOWNLOAD_PATH)
    if os.name == "nt":
        nim_zip = os.path.join(temp_dir, "nim.zip")
        if r.status_code == 200:
            with open(nim_zip, "wb") as f:
                f.write(r.content)
        prg_path = os.path.join(data_path, "prg")
        os.makedirs(prg_path, exist_ok=True)

        with zipfile.ZipFile(nim_zip) as f:
            f.extractall(prg_path)

    else:
        nim_tar_xz = os.path.join(temp_dir, "nim.tar.xz")
        nim_tar = os.path.join(temp_dir, "nim.tar")
        if r.status_code == 200:
            with open(nim_tar_xz, "wb") as f:
                f.write(r.content)

        buf = lzma.open(nim_tar_xz).read()
        with open(nim_tar, "wb") as f:
            f.write(buf)

        prg_path = os.path.join(data_path, "prg")
        os.makedirs(prg_path, exist_ok=True)

        with tarfile.open(nim_tar, "r") as tar:
            tar.extractall(prg_path)

    nim_path = get_nim_path(data_path)
    if nim_path:
        nim_cfg_path = os.path.join(nim_path, "config", "nim.cfg")
        with open(nim_cfg_path, "rt") as f:
            buf = f.read()
            buf = buf.replace(
                "cc = gcc", "cc = clang\nclang.exe = zigcc\nclang.linkerexe = zigcc\n"
            )
        with open(nim_cfg_path, "wt") as f:
            f.write(buf)

        zigcc_bin = os.path.join(
            nim_path, "bin", "zigcc.exe" if os.name == "nt" else "zigcc"
        )
        zigcc_c = os.path.join(temp_dir, "zigcc.c")
        with open(zigcc_c, "wt") as f:
            f.write(ZIG_CC_C)

        exit_code, output_tab, err_tab = run(
            ["ptig", "zig", "cc", "-o", zigcc_bin, zigcc_c], env=os.environ
        )
        if err_tab:
            print(err_tab)

        if os.name != "nt":
            st = os.stat(zigcc_bin)
            os.chmod(zigcc_bin, st.st_mode | stat.S_IEXEC)


def get_nim_path(data_path):
    prg_path = os.path.join(data_path, "prg")
    if not os.path.exists(prg_path):
        return None
    dir_list = os.listdir(prg_path)
    for item in dir_list:
        if item.startswith("nim-"):
            return os.path.join(prg_path, item)
    return None


def install_if_not_exists(data_path):
    nim_path = get_nim_path(data_path)
    if nim_path:
        return nim_path
    else:
        install_nim(data_path)
        return get_nim_path(data_path)
