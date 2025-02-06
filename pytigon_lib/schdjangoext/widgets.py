import django.forms.widgets


class ImgFileInput(django.forms.widgets.ClearableFileInput):
    """
    A custom file input widget for handling image file inputs.
    This widget extends ClearableFileInput to handle image files specifically.
    """

    def format_value(self, value):
        """
        Format the value to be displayed in the widget.

        Args:
            value: The value to be formatted.

        Returns:
            The formatted value.
        """
        return value

    def value_from_datadict(self, data, files, name):
        """
        Extract the value from the data dictionary.

        Args:
            data: The data dictionary containing form data.
            files: The files dictionary containing uploaded files.
            name: The name of the field.

        Returns:
            The value extracted from the data or files dictionary, or None if not found.
        """
        try:
            if name in data:
                return data[name]
            elif name in files:
                return files[name]
            else:
                return None
        except Exception as e:
            # Log the error or handle it as needed
            raise ValueError(f"Error extracting value from datadict: {e}")
