from pytigon_lib.schdjangoext.django_ihtml import *

# Pytest tests
import pytest


def test_fa_icons():
    """Test the fa_icons function."""
    assert fa_icons("test") == "<i class='fa fa-test'></i>"


def test_ihtml_to_html_failure():
    """Test ihtml_to_html with an error during conversion."""
    result = ihtml_to_html("invalid_file", "<div>Test</div>")
    assert result == ""


if __name__ == "__main__":
    pytest.main()
