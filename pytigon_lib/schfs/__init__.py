"""Virtual File System (VFS) tools for the pytigon framework.

Provides convenience wrappers for file operations that work transparently
with both the local filesystem and Django's virtual filesystem storage.
"""

from django.core.files.storage import default_storage

from pytigon_lib.schfs.vfstools import (
    extractall,
    get_temp_filename,
    get_unique_filename,
    open_and_create_dir,
    open_file,
)


def get_vfs():
    """Retrieve the default virtual file system (VFS) from Django's default storage.

    Returns:
        The default VFS object provided by Django's storage backend.

    Raises:
        RuntimeError: If the default storage does not expose a 'fs' attribute,
            which typically indicates a misconfigured storage backend.
    """
    try:
        return default_storage.fs
    except AttributeError as e:
        raise RuntimeError(
            "Failed to retrieve the default VFS: the storage backend does not "
            "expose a 'fs' attribute. Check your Django storage configuration."
        ) from e
