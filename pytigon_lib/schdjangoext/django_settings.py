import os

from django.contrib.staticfiles.finders import AppDirectoriesFinder


class AppPackDirectoriesFinder(AppDirectoriesFinder):
    """Custom static file finder that looks for files in a specific 'static'
    directory relative to the app package path.

    Overrides the default AppDirectoriesFinder to use '../static' as the
    source directory, allowing static files to reside outside the app
    module directory.
    """

    source_dir = "../static"

    def __init__(self, *args, **kwargs):
        """Initialize the finder with the custom source directory.

        Builds storage mappings for each app configuration pointing to
        the custom static directory path.
        """
        super().__init__(*args, **kwargs)
        self.storages = {
            app_config.name: self.storage_class(
                os.path.join(app_config.path, self.source_dir)
            )
            for app_config in self.app_configs
        }
