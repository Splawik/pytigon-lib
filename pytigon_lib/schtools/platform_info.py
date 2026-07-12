import logging
import platform
from os import environ

_logger = logging.getLogger(__name__)


def platform_name():
    """Determine the platform name.

    Returns:
        str: The name of the platform (e.g., 'Linux', 'Android', 'Windows', etc.).
    """
    try:
        system_name = platform.system()
        if system_name == "Linux" and "ANDROID_ARGUMENT" in environ:
            return "Android"
        return system_name
    except Exception as e:
        _logger.warning("Error determining platform: %s", e)
        return "Unknown"
