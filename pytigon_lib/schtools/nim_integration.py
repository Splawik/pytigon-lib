import lzma
import httpx
import tarfile
import os
import tempfile

if os.name == "nt":
    NIM_DOWNLOAD_PATH = "https://nim-lang.org/download/nim-2.0.4_x64.zip"
else:
    NIM_DOWNLOAD_PATH = "https://nim-lang.org/download/nim-2.0.4-linux_x64.tar.xz"


def install_nim(data_path):
    temp_dir = tempfile.gettempdir()
    nim_tar_xz = os.path.join(temp_dir, "nim.tar.xz")
    nim_tar = os.path.join(temp_dir, "nim.tar")
    r = httpx.get(NIM_DOWNLOAD_PATH)
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

    nim_lib_path = os.path.join(prg_path, "lib")
    os.makedirs(nim_lib_path)


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
