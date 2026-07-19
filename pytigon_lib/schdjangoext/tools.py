import importlib
import logging
import sys

from django.conf import settings

_logger = logging.getLogger(__name__)


def import_model(app, tab):
    """Import the model module for the specified application and return the model class.

    Args:
        app (str): The name of the Django application.
        tab (str): The name of the model class.

    Returns:
        Model: The model class if found, otherwise None.
    """
    try:
        module_path = f"{app}.models"
        module = sys.modules.get(module_path)

        if not module:
            module = importlib.import_module(module_path)

        return getattr(module, tab)

    except (ImportError, AttributeError):
        _logger.debug("Could not import model %s.%s", app, tab, exc_info=True)
        return None


def gettempdir():
    """Get the temporary directory path from Django settings.

    Returns:
        str: The path to the temporary directory.
    """
    return settings.TEMP_PATH


def make_href(href, base_url=None):
    """Construct a URL by combining the given href with the base URL and settings.

    Args:
        href (str): The relative or absolute URL.
        base_url (str, optional): The base URL to append query parameters from. Defaults to None.

    Returns:
        str: The constructed URL.
    """
    if settings.URL_ROOT_FOLDER and href.startswith("/"):
        href = f"/{settings.URL_ROOT_FOLDER}{href}"

    if base_url and "?" in base_url:
        query_params = base_url.split("?", 1)[1]
        href += f"&{query_params}" if "?" in href else f"?{query_params}"

    return href


def from_migrations():
    """Check if the current command is related to migrations.

    Returns:
        bool: True if the command is related to migrations, otherwise False.
    """
    migration_commands = {"makemigrations", "makeallmigrations", "exporttolocaldb"}
    return any(cmd in sys.argv for cmd in migration_commands)
