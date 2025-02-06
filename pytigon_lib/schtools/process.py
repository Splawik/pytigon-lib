import sys
import os
import asyncio
from subprocess import Popen, PIPE
from threading import Thread
from typing import List, Tuple, Optional

from pytigon_lib.schtools.tools import get_executable
from pytigon_lib.schtools.platform_info import platform_name


class FrozenModules:
    """Class to manage freezing and restoring Python modules."""

    def __init__(self):
        """Initialize FrozenModules by storing and deleting specific modules."""
        self.to_restore = {}
        self.all = list(sys.modules.keys())
        to_delete = []

        for module_name in self.all:
            if any(
                module_name.startswith(prefix)
                for prefix in ("django", "pytigon_lib", "schserw", "settings")
            ):
                self.to_restore[module_name] = sys.modules[module_name]
                to_delete.append(module_name)

        for module_name in to_delete:
            del sys.modules[module_name]

    def restore(self):
        """Restore the previously frozen modules."""
        to_delete = [
            module_name for module_name in sys.modules if module_name not in self.all
        ]

        for module_name in to_delete:
            del sys.modules[module_name]

        for module_name, module in self.to_restore.items():
            sys.modules[module_name] = module


def run(
    cmd: List[str], shell: bool = False, env: Optional[dict] = None
) -> Tuple[int, Optional[List[str]], Optional[List[str]]]:
    """Run an external command and capture its output.

    Args:
        cmd: List of command arguments.
        shell: Whether to use the shell to execute the command.
        env: Environment variables to use.

    Returns:
        A tuple containing:
            - The exit code of the command.
            - The stdout output as a list of strings.
            - The stderr output as a list of strings.
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
    """Run a Python script using the current Python interpreter.

    Args:
        cmd: List of command arguments.

    Returns:
        A tuple containing:
            - The exit code of the command.
            - The stdout output as a list of strings.
            - The stderr output as a list of strings.
    """
    return run([get_executable()] + cmd)


def _manage(path: str, cmd: List[str]):
    """Internal function to manage Django commands.

    Args:
        path: The directory path to run the command in.
        cmd: List of command arguments.
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

    Args:
        cmd: List of command arguments.
        thread_version: Whether to run the command in a separate thread.

    Returns:
        A tuple containing:
            - The exit code of the command.
            - The stdout output as a list of strings.
            - The stderr output as a list of strings.
    """
    if platform_name() == "Emscripten":
        return (None, None, None)

    if not cmd:
        return (0, [], [])

    if thread_version:
        thread = Thread(target=_manage, args=(os.getcwd(), cmd))
        thread.start()
        thread.join()
        return 0, [], []
    else:
        return py_run(["manage.py"] + cmd)
