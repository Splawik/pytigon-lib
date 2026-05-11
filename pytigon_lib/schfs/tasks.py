"""Background task handlers for file system operations (delete, copy, move).

These operations work through Django's default storage virtual filesystem,
supporting both individual files and directory trees.
"""

from __future__ import annotations

import logging
import posixpath
from typing import Any, Optional

from django.core.files.storage import default_storage

logger = logging.getLogger(__name__)


def filesystemcmd(cproxy: Optional[Any] = None, **kwargs: Any) -> None:
    """Execute a batch file-system command (DELETE, COPY, or MOVE) via the VFS.

    Designed to run as a background task. Sends "start"/"stop" events
    through *cproxy* if provided so the caller can track progress.

    Args:
        cproxy: An optional proxy object with a ``send_event(str)`` method,
            used to signal the beginning and end of the operation.
        **kwargs: Must contain a ``param`` dict with the following keys:
            * **cmd** (str): One of ``"DELETE"``, ``"COPY"``, ``"MOVE"``.
            * **files** (list[str]): Source paths to operate on.
            * **dest** (str, optional): Destination directory for COPY/MOVE.
              If omitted for COPY or MOVE the behaviour is undefined; the
              caller should provide it.

    Raises:
        ValueError: If *cmd* or *files* is missing / empty, or if *cmd* is not
            one of the recognised operations.
    """
    try:
        if cproxy:
            cproxy.send_event("start")

        param: dict[str, Any] = kwargs.get("param", {})
        cmd: str = param.get("cmd", "")
        files: list[str] = param.get("files", [])
        dest: str = param.get("dest", "")
        if dest:
            dest = dest.rstrip("/") + "/"

        if not cmd or not files:
            raise ValueError("Missing 'cmd' or 'files' in parameters.")

        if cmd == "DELETE":
            for f in files:
                try:
                    if default_storage.fs.isfile(f):
                        default_storage.fs.remove(f)
                    else:
                        default_storage.fs.removetree(f)
                except Exception:
                    logger.exception("Error deleting '%s'", f)

        elif cmd == "COPY":
            for f in files:
                try:
                    name = posixpath.basename(f)
                    if default_storage.fs.isfile(f):
                        default_storage.fs.copy(f, dest + name, overwrite=True)
                    else:
                        default_storage.fs.copydir(
                            f, dest + name, overwrite=True, ignore_errors=True
                        )
                except Exception:
                    logger.exception("Error copying '%s'", f)

        elif cmd == "MOVE":
            for f in files:
                try:
                    name = posixpath.basename(f)
                    if default_storage.fs.isfile(f):
                        default_storage.fs.move(f, dest + name, overwrite=True)
                    else:
                        default_storage.fs.movedir(
                            f, dest + name, overwrite=True, ignore_errors=True
                        )
                except Exception:
                    logger.exception("Error moving '%s'", f)

        else:
            raise ValueError(f"Unsupported command: '{cmd}'")

    except ValueError:
        # Re-raise validation errors so the caller can react to them.
        raise

    except Exception:
        logger.exception("Unexpected error during filesystem command '%s'", cmd)
    finally:
        if cproxy:
            cproxy.send_event("stop")
