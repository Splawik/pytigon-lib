"""Custom Django form widgets.

Provides :class:`ImgFileInput`, a :class:`ClearableFileInput` variant
tailored for image uploads.
"""

import django.forms.widgets


class ImgFileInput(django.forms.widgets.ClearableFileInput):
    """A file input widget optimized for image uploads.

    Extends :class:`~django.forms.ClearableFileInput` to handle image
    files specifically. The ``format_value`` override simply passes
    through the value unchanged.
    """

    def format_value(self, value):
        """Return the value unchanged.

        Overrides the parent behaviour to preserve the raw value
        without any transformation.

        Args:
            value: The field value (can be any type, including ``None``).

        Returns:
            The same value, with no transformation applied.
        """
        return value

    def value_from_datadict(self, data, files, name):
        """Extract the field value from form data or uploaded files.

        Looks up ``name`` in ``data`` first, then in ``files``.
        ``data`` takes priority when the key exists in both dictionaries.
        Returns ``None`` if neither contains the key.

        Args:
            data: Form data dictionary (mapping-like).
            files: Uploaded files dictionary (mapping-like).
            name: Field name to look up.

        Returns:
            The extracted value, or ``None``.

        Raises:
            TypeError: If ``data`` is ``None`` (not a valid mapping).
        """
        if name in data:
            return data[name]
        if name in files:
            return files[name]
        return None
