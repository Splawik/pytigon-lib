import os
import environ
from typing import Optional

# Global environment variable instance
ENV = None


def get_environ(path: Optional[str] = None) -> environ.Env:
    """Initialize and return the environment configuration.

    Args:
        path (Optional[str]): Path to the directory containing .env or env file.

    Returns:
        environ.Env: The environment configuration instance.
    """
    global ENV

    if ENV is None:
        ENV = environ.Env(
            DEBUG=(bool, False),
            PYTIGON_DEBUG=(bool, False),
            EMBEDED_DJANGO_SERVER=(bool, False),
            PYTIGON_WITHOUT_CHANNELS=(bool, False),
            PYTIGON_TASK=(bool, False),
            LOGS_TO_DOCKER=(bool, False),
            PWA=(bool, False),
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
                    ENV.read_env(env_path)
                except Exception as e:
                    print(f"Error reading environment file {env_path}: {e}")

    return ENV
