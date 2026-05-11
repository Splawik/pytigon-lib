"""Tests for :class:`pytigon_lib.schdjangoext.widgets.ImgFileInput`."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.forms.widgets import ClearableFileInput

from pytigon_lib.schdjangoext.widgets import ImgFileInput


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def widget():
    """Return a fresh :class:`ImgFileInput` instance."""
    return ImgFileInput()


@pytest.fixture
def uploaded_file():
    """Return a simple uploaded file for tests."""
    return SimpleUploadedFile("test.jpg", b"file_content")


# ---------------------------------------------------------------------------
# Inheritance / type checks
# ---------------------------------------------------------------------------


def test_is_clearable_file_input_subclass():
    """ImgFileInput should be a subclass of Django's ClearableFileInput."""
    assert issubclass(ImgFileInput, ClearableFileInput)


# ---------------------------------------------------------------------------
# format_value
# ---------------------------------------------------------------------------


def test_format_value_with_string(widget):
    """Strings pass through unchanged."""
    assert widget.format_value("test_value") == "test_value"


def test_format_value_with_none(widget):
    """None passes through unchanged (important for empty fields)."""
    assert widget.format_value(None) is None


def test_format_value_with_empty_string(widget):
    """Empty strings pass through unchanged."""
    assert widget.format_value("") == ""


def test_format_value_with_uploaded_file(widget, uploaded_file):
    """Uploaded file objects pass through unchanged."""
    assert widget.format_value(uploaded_file) is uploaded_file


# ---------------------------------------------------------------------------
# value_from_datadict – happy paths
# ---------------------------------------------------------------------------


def test_value_from_datadict_from_data(widget):
    """Value is returned from ``data`` when present."""
    data = {"image": "test_image"}
    files = {}
    assert widget.value_from_datadict(data, files, "image") == "test_image"


def test_value_from_datadict_from_files(widget, uploaded_file):
    """Value is returned from ``files`` when not in ``data``."""
    data = {}
    files = {"image": uploaded_file}
    assert widget.value_from_datadict(data, files, "image") is uploaded_file


def test_value_from_datadict_data_priority(widget, uploaded_file):
    """``data`` takes priority when the key exists in both dicts."""
    data = {"image": "from_data"}
    files = {"image": uploaded_file}
    assert widget.value_from_datadict(data, files, "image") == "from_data"


def test_value_from_datadict_not_found(widget):
    """Returns ``None`` when the key is absent from both dicts."""
    data = {}
    files = {}
    assert widget.value_from_datadict(data, files, "image") is None


def test_value_from_datadict_empty_data_but_in_files(widget, uploaded_file):
    """When ``data`` is empty but ``files`` has the key, returns file."""
    data = {}
    files = {"image": uploaded_file}
    assert widget.value_from_datadict(data, files, "image") is uploaded_file


# ---------------------------------------------------------------------------
# value_from_datadict – error paths
# ---------------------------------------------------------------------------


def test_value_from_datadict_data_none(widget):
    """Calling with ``data=None`` raises TypeError (not iterable)."""
    with pytest.raises(TypeError):
        widget.value_from_datadict(None, {}, "image")


def test_value_from_datadict_files_none_found_in_data(widget):
    """``files=None`` is fine as long as the key is in ``data``."""
    data = {"image": "found"}
    assert widget.value_from_datadict(data, None, "image") == "found"


# ---------------------------------------------------------------------------
# value_from_datadict – edge cases
# ---------------------------------------------------------------------------


def test_value_from_datadict_with_numeric_key():
    """Works with numeric keys (Django form field names are strings, but be safe)."""
    widget = ImgFileInput()
    data = {0: "zero"}
    assert widget.value_from_datadict(data, {}, 0) == "zero"


def test_value_from_datadict_with_falsy_value(widget):
    """Falsy values (empty string, 0) are still returned when key exists."""
    data = {"field": ""}
    assert widget.value_from_datadict(data, {}, "field") == ""
