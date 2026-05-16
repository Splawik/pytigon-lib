import os
import environ
from typing import Optional

# Global environment variable instance (singleton)
_ENV = None


def get_environ(path: Optional[str] = None) -> environ.Env:
    """Initialize and return the environment configuration singleton.

    On first call, creates an environ.Env instance with default settings.
    Subsequent calls return the same instance. If a path is provided and an
    environment file (.env or 'env') is found there, it is read once per path.

    Args:
        path: Directory path where .env or env file is located.
              If None, only environment variables already set in the OS
              are considered.

    Returns:
        environ.Env: The environment configuration instance.

    Raises:
        environ.ImproperlyConfigured: If a required variable is missing
            and no default was provided.
    """
    global _ENV

    if _ENV is None:
        _ENV = environ.Env(
            DEBUG=(bool, False),
            PYTIGON_DEBUG=(bool, False),
            EMBEDED_DJANGO_SERVER=(bool, False),
            PYTIGON_WITHOUT_CHANNELS=(bool, False),
            PYTIGON_TASK=(bool, False),
            LOGS_TO_DOCKER=(bool, False),
            PWA=(bool, False),
            PUBLIC=(bool, False),
            GRAPHQL=(bool, False),
            DJANGO_Q=(bool, False),
            ALLAUTH=(bool, False),
            REST=(bool, False),
            CANCAN_ENABLED=(bool, False),
            SENTRY_ENABLED=(bool, False),
            PROMETHEUS_ENABLED=(bool, False),
            COMPRESS_ENABLED=(bool, False),
            SECRET_KEY=(str, ""),
            CHANNELS_REDIS=(str, ""),
            PUBLISH_IN_SUBFOLDER=(str, ""),
            THUMBNAIL_PROTECTED=(bool, False),
            MAILER=(bool, True),
            LOG_VIEWER=(bool, False),
            SCRIPT_MODE=(bool, False),
        )

    if path:
        env_paths = [os.path.join(path, ".env"), os.path.join(path, "env")]
        for env_path in env_paths:
            if os.path.exists(env_path):
                try:
                    _ENV.read_env(env_path)
                except Exception as e:
                    print(f"Error reading environment file {env_path}: {e}")

    return _ENV
