"""Subprocess and Django management command execution utilities."""

import asyncio
import os
import sys
from subprocess import PIPE, Popen
from threading import Thread
from typing import List, Optional, Tuple

from pytigon_lib.schtools.platform_info import platform_name
from pytigon_lib.schtools.tools import get_executable


class FrozenModules:
    """Context manager-like helper to temporarily remove and restore modules.

    Removes Django/pytigon-related modules from sys.modules so that a
    sub-interpreter or management command can import them fresh. Call
    ``restore()`` to put them back.

    Usage::

        frozen = FrozenModules()
        try:
            # run code that re-imports modules
        finally:
            frozen.restore()
    """

    def __init__(self):
        """Store and remove tracked modules from sys.modules."""
        self.to_restore = {}
        self.original_keys = set(sys.modules.keys())
        to_delete = []

        for module_name in self.original_keys:
            if any(
                module_name.startswith(prefix)
                for prefix in ("django", "pytigon_lib", "schserw", "settings")
            ):
                self.to_restore[module_name] = sys.modules[module_name]
                to_delete.append(module_name)

        for module_name in to_delete:
            del sys.modules[module_name]

    def restore(self):
        """Restore previously removed modules and clean up any new ones."""
        # Remove modules that were added after freezing
        to_delete = [name for name in sys.modules if name not in self.original_keys]

        for name in to_delete:
            del sys.modules[name]

        # Restore original modules
        for name, module in self.to_restore.items():
            sys.modules[name] = module


def run(
    cmd: List[str], shell: bool = False, env: Optional[dict] = None
) -> Tuple[int, Optional[List[str]], Optional[List[str]]]:
    """Run an external command and capture stdout and stderr.

    Args:
        cmd: Command and arguments as a list of strings.
        shell: If True, run the command through the system shell.
        env: Optional environment variable dictionary.

    Returns:
        Tuple of (exit_code, stdout_lines, stderr_lines). Lines are
        lists of strings without trailing carriage returns. None means
        no output was captured.
    """
    try:
        process = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=shell, env=env)
        output, err = process.communicate()
        exit_code = process.wait()

        output_tab = (
            [line.replace("\r", "") for line in output.decode("utf-8").split("\n")]
            if output
            else None
        )
        err_tab = (
            [line.replace("\r", "") for line in err.decode("utf-8").split("\n")]
            if err
            else None
        )

        return exit_code, output_tab, err_tab
    except Exception as e:
        print(f"Error running command {cmd}: {e}", file=sys.stderr)
        return -1, None, None


def py_run(cmd: List[str]) -> Tuple[int, Optional[List[str]], Optional[List[str]]]:
    """Run a Python command using the current interpreter.

    Prepends the path to the current Python executable to the command list.

    Args:
        cmd: Arguments to pass to the Python interpreter.

    Returns:
        Same as :func:`run`.
    """
    return run([get_executable()] + cmd)


def _manage(path: str, cmd: List[str]):
    """Execute a Django management command in a clean module environment.

    Freezes existing Django modules so the management command can import
    them fresh, and runs the command in a new asyncio event loop.

    Args:
        path: Working directory for the command.
        cmd: Management command arguments.
    """
    frozen_modules = FrozenModules()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    os.chdir(path)

    try:
        m = __import__("pytigon_lib.schdjangoext.django_manage")
        sys.path.insert(0, path)
        m.schdjangoext.django_manage.cmd(cmd, from_main=False)
    finally:
        sys.path.pop(0)
        frozen_modules.restore()


def py_manage(
    cmd: List[str], thread_version: bool = False
) -> Tuple[int, Optional[List[str]], Optional[List[str]]]:
    """Run a Django management command.

    On Emscripten, returns (0, [], []) as a no-op since management
    commands cannot be forked.

    Args:
        cmd: Management command arguments.
        thread_version: If True, run in a separate thread (used when
            the current process is already a Django management context).

    Returns:
        Same as :func:`run`.
    """
    if platform_name() == "Emscripten":
        return 0, [], []

    if not cmd:
        return 0, [], []

    if thread_version:
        thread = Thread(target=_manage, args=(os.getcwd(), cmd))
        thread.start()
        thread.join()
        return 0, [], []
    else:
        return py_run(["manage.py"] + cmd)
