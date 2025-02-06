from importlib import import_module
from django.apps.config import AppConfig, MODELS_MODULE_NAME
from django.utils.module_loading import module_has_submodule


class AppConfigMod(AppConfig):
    """Custom AppConfig class with extended functionality."""

    def __init__(self, app_name, app_module):
        """
        Initialize the AppConfigMod instance.

        Args:
            app_name (str): Name of the application.
            app_module (str): Module name of the application.
        """
        super().__init__(app_name, app_module)

    def import_models(self, all_models=None):
        """Import models for the application.

        Args:
            all_models (dict, optional): Dictionary of all models. Defaults to None.
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
        """Add two AppConfigMod instances by their names.

        Args:
            other (AppConfigMod): Another AppConfigMod instance.

        Returns:
            str: Concatenated names of the two instances.
        """
        return self.name + other


def get_app_config(app_name):
    """Get an AppConfigMod instance for the given app name.

    Args:
        app_name (str): Name of the application.

    Returns:
        AppConfigMod: An instance of AppConfigMod.
    """
    return AppConfigMod.create(app_name.split(".")[1] if "." in app_name else app_name)


def get_app_name(app):
    """Get the name of the application.

    Args:
        app (AppConfig or str): The application instance or name.

    Returns:
        str: The name of the application.
    """
    return app.name if isinstance(app, AppConfig) else app
