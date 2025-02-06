from pytigon_lib.schdjangoext.widgets import *

# Pytest tests for ImgFileInput
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile


@pytest.fixture
def img_file_input():
    return ImgFileInput()


def test_format_value(img_file_input):
    """
    Test the format_value method of ImgFileInput.
    """
    assert img_file_input.format_value("test_value") == "test_value"


def test_value_from_datadict_with_data(img_file_input):
    """
    Test value_from_datadict when the value is in the data dictionary.
    """
    data = {"image": "test_image"}
    files = {}
    assert img_file_input.value_from_datadict(data, files, "image") == "test_image"


def test_value_from_datadict_with_files(img_file_input):
    """
    Test value_from_datadict when the value is in the files dictionary.
    """
    data = {}
    files = {"image": SimpleUploadedFile("test.jpg", b"file_content")}
    assert img_file_input.value_from_datadict(data, files, "image") == files["image"]


def test_value_from_datadict_not_found(img_file_input):
    """
    Test value_from_datadict when the value is not found in either data or files.
    """
    data = {}
    files = {}
    assert img_file_input.value_from_datadict(data, files, "image") is None


def test_value_from_datadict_error_handling(img_file_input):
    """
    Test error handling in value_from_datadict.
    """
    with pytest.raises(ValueError):
        img_file_input.value_from_datadict(None, None, "image")
