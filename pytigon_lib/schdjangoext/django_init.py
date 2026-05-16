"""Custom Django AppConfig with extended initialization.

Provides :class:`AppConfigMod` which adds a concatenation operator
and a smarter model-import mechanism.
"""

from importlib import import_module

from django.apps.config import MODELS_MODULE_NAME, AppConfig
from django.utils.module_loading import module_has_submodule


class AppConfigMod(AppConfig):
    """Extended :class:`AppConfig` with custom model import and string
    concatenation support."""

    def __init__(self, app_name, app_module):
        """Initialize the application configuration.

        Args:
            app_name: Application name string.
            app_module: Application module.
        """
        super().__init__(app_name, app_module)

    def import_models(self, all_models=None):
        """Import models for this application.

        If the application module has a ``models`` submodule it is
        imported explicitly.

        Args:
            all_models: Optional pre-loaded models dictionary. If not
                given, ``self.apps.all_models`` is used.
        """
        self.models = (
            self.apps.all_models[self.label] if all_models is None else all_models
        )

        if module_has_submodule(self.module, MODELS_MODULE_NAME):
            models_module_name = f"{self.name}.{MODELS_MODULE_NAME}"
            try:
                self.models_module = import_module(models_module_name)
            except ImportError:
                self.models_module = None

    def __add__(self, other):
        """Concatenate the name of this app config with another.

        This is a convenience operator allowing expressions such as
        ``app_config + "suffix"`` to produce the app's name followed
        by a string suffix. When combined with another
        :class:`AppConfigMod` instance the two names are concatenated.

        Args:
            other: Another :class:`AppConfigMod` instance or a string.

        Returns:
            The concatenated string.
        """
        if isinstance(other, AppConfigMod):
            return self.name + other.name
        return self.name + str(other)


def get_app_config(app_name):
    """Create an :class:`AppConfigMod` instance for an application name.

    Handles fully-qualified dotted names by extracting the last
    component.

    Args:
        app_name: Dotted or simple application name.

    Returns:
        An :class:`AppConfigMod` instance.
    """
    return AppConfigMod.create(app_name.split(".")[-1] if "." in app_name else app_name)


def get_app_name(app):
    """Safely extract the application name.

    Args:
        app: An :class:`AppConfig` instance or a plain string name.

    Returns:
        The application name string.
    """
    return app.name if isinstance(app, AppConfig) else str(app)
