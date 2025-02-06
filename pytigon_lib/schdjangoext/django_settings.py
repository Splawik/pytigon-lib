from django.contrib.staticfiles.finders import AppDirectoriesFinder


class AppPackDirectoriesFinder(AppDirectoriesFinder):
    """Custom static file finder that looks for files in a specific directory."""

    source_dir = "../static"

    def __init__(self, *args, **kwargs):
        """Initialize the finder with the custom source directory."""
        super().__init__(*args, **kwargs)
        self.storages = {
            app_config.name: self.storage_class(
                os.path.join(app_config.path, self.source_dir)
            )
            for app_config in self.app_configs
        }
