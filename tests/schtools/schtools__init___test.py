from pytigon_lib.schtools import *

# Pytest tests for sch_import function
import pytest


def test_sch_import_success():
    """Test successful import of a standard library module."""
    math_module = sch_import("math")
    assert math_module.sqrt(4) == 2.0


def test_sch_import_nested_module():
    """Test successful import of a nested module."""
    os_path_module = sch_import("os.path")
    assert os_path_module.join("a", "b") == "a/b"


def test_sch_import_failure():
    """Test import failure for a non-existent module."""
    with pytest.raises(ImportError):
        sch_import("non_existent_module")


def test_sch_import_attribute_error():
    """Test import failure due to missing attribute."""
    with pytest.raises(ImportError):
        sch_import("os.non_existent_attribute")


if __name__ == "__main__":
    pytest.main()
