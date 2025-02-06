from django.core.files.storage import default_storage
import logging

# Configure logging
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


def filesystemcmd(cproxy=None, **kwargs):
    """Background tasks related to file system operations.

    Args:
        cproxy: Optional proxy object to send events.
        **kwargs: Keyword arguments containing 'param' dictionary with 'cmd', 'files', and optionally 'dest'.
    """
    try:
        if cproxy:
            cproxy.send_event("start")

        param = kwargs.get("param", {})
        cmd = param.get("cmd")
        files = param.get("files", [])
        dest = param.get("dest", "") + "/" if "dest" in param else ""

        if not cmd or not files:
            raise ValueError("Missing 'cmd' or 'files' in parameters.")

        if cmd == "DELETE":
            for f in files:
                try:
                    if default_storage.fs.isfile(f):
                        default_storage.fs.remove(f)
                    else:
                        default_storage.fs.removetree(f)
                except Exception as e:
                    logger.error(f"Error deleting {f}: {e}")

        elif cmd == "COPY":
            for f in files:
                try:
                    name = f.rsplit("/", 1)[-1]
                    if default_storage.fs.isfile(f):
                        default_storage.fs.copy(f, dest + name, overwrite=True)
                    else:
                        default_storage.fs.copydir(
                            f, dest + name, overwrite=True, ignore_errors=True
                        )
                except Exception as e:
                    logger.error(f"Error copying {f}: {e}")

        elif cmd == "MOVE":
            for f in files:
                try:
                    name = f.rsplit("/", 1)[-1]
                    if default_storage.fs.isfile(f):
                        default_storage.fs.move(f, dest + name, overwrite=True)
                    else:
                        default_storage.fs.movedir(
                            f, dest + name, overwrite=True, ignore_errors=True
                        )
                except Exception as e:
                    logger.error(f"Error moving {f}: {e}")

        else:
            raise ValueError(f"Unsupported command: {cmd}")

    except ValueError as e:
        raise ValueError(e)

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        if cproxy:
            cproxy.send_event("stop")
