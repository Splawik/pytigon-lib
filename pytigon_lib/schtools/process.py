"""Subprocess and Django management command execution utilities."""

import asyncio
import importlib
import logging
import os
import sys
from subprocess import PIPE, Popen
from threading import Thread

from pytigon_lib.schtools.platform_info import platform_name
from pytigon_lib.schtools.tools import get_executable

_logger = logging.getLogger(__name__)


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
    cmd: list[str], shell: bool = False, env: dict | None = None
) -> tuple[int, list[str] | None, list[str] | None]:
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
        _logger.error("Error running command %s: %s", cmd, e)
        return -1, None, None


def py_run(cmd: list[str]) -> tuple[int, list[str] | None, list[str] | None]:
    """Run a Python command using the current interpreter.

    Prepends the path to the current Python executable to the command list.

    Args:
        cmd: Arguments to pass to the Python interpreter.

    Returns:
        Same as :func:`run`.
    """
    return run([get_executable()] + cmd)


def _manage(path: str, cmd: list[str]):
    """Execute a Django management command in a clean module environment.

    Freezes existing Django modules so the management command can import
    them fresh, and runs the command in a new asyncio event loop.

    Args:
        path: Working directory for the command.
        cmd: Management command arguments.
    """
    original_cwd = os.getcwd()
    frozen_modules = FrozenModules()

    prev_loop = asyncio.get_event_loop_policy().get_event_loop()
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        os.chdir(path)

        sys.path.insert(0, path)
        m = importlib.import_module("pytigon_lib.schdjangoext.django_manage")
        m.cmd(cmd, from_main=False)
    finally:
        sys.path.pop(0)
        os.chdir(original_cwd)
        frozen_modules.restore()
        loop.close()
        asyncio.set_event_loop(prev_loop)


def py_manage(
    cmd: list[str], thread_version: bool = False
) -> tuple[int, list[str] | None, list[str] | None]:
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
        result_holder: dict = {"exc": None}

        def _thread_target():
            try:
                _manage(os.getcwd(), cmd)
            except Exception as exc:
                result_holder["exc"] = exc

        thread = Thread(target=_thread_target, args=())
        thread.start()
        thread.join()
        if result_holder["exc"] is not None:
            _logger.error("Threaded py_manage failed: %s", result_holder["exc"])
            return 1, [], [str(result_holder["exc"])]
        return 0, [], []
    else:
        return py_run(["manage.py"] + cmd)
