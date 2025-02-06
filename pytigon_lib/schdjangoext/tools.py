import sys
import traceback
from django.conf import settings


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
            module = __import__(module_path, fromlist=["models"])

        models = getattr(module, "models", module)
        return getattr(models, tab)

    except (ImportError, AttributeError) as e:
        traceback.print_exc()
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
