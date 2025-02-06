from pytigon_lib.schfs.vfstools import (
    open_file,
    open_and_create_dir,
    get_unique_filename,
    get_temp_filename,
    extractall,
)
from django.core.files.storage import default_storage


def get_vfs():
    """Retrieve the default virtual file system (VFS) from Django's default storage.

    Returns:
        The default VFS object.
    """
    try:
        return default_storage.fs
    except AttributeError as e:
        raise RuntimeError("Failed to retrieve the default VFS.") from e
