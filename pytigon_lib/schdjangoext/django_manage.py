import os
import sys
import django
from django.core.management import execute_from_command_line


def cmd(arg, from_main=False):
    """
    Execute a Django management command.

    Args:
        arg (str or list): The command to execute. If a string, it will be converted to a list.
        from_main (bool): If True, `arg` is treated as the full command line arguments.

    Raises:
        SystemExit: If the command execution fails.
    """
    try:
        if from_main:
            argv = arg
        else:
            argv = ["manage.py"] + ([arg] if isinstance(arg, str) else arg)

        os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings_app")
        execute_from_command_line(argv)
    except Exception as e:
        print(f"Error executing command: {e}", file=sys.stderr)
        sys.exit(1)


def syncdb():
    """Synchronize the database."""
    cmd("syncdb")


def help():
    """Display help information."""
    cmd("help")


if __name__ == "__main__":
    cmd(sys.argv, from_main=True)
