import os
import tempfile

os.environ["SECRET_KEY"] = "test-key"
os.environ["SCRIPT_MODE"] = "1"

import django
from django.conf import settings

if not settings.configured:
    settings.configure(
        SECRET_KEY="test-key",
        INSTALLED_APPS=[
            "django.contrib.contenttypes",
            "django.contrib.auth",
        ],
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
                "NAME": ":memory:",
            }
        },
        TEMP_PATH=tempfile.gettempdir(),
        DEFAULT_FILE_STORAGE="django.core.files.storage.InMemoryStorage",
    )
    django.setup()
