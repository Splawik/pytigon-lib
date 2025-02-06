import platform
from os import environ


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
        print(f"Error determining platform: {e}")
        return "Unknown"
