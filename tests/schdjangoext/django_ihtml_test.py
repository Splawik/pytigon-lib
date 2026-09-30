# Pytest tests
import pytest
from django.template import TemplateSyntaxError

from pytigon_lib.schdjangoext.django_ihtml import *


def test_fa_icons():
    """Test the fa_icons function."""
    assert fa_icons("test") == "<i class='fa fa-test'></i>"


def test_removed_django_tags_not_auto_closed():
    """ifequal/ifnotequal were removed in Django 4.0 and must not be emitted."""
    assert "ifequal" not in AUTO_CLOSE_DJANGO_ELEM
    assert "ifnotequal" not in AUTO_CLOSE_DJANGO_ELEM
    assert "if" in AUTO_CLOSE_DJANGO_ELEM
    assert "for" in AUTO_CLOSE_DJANGO_ELEM


def test_tag_lists_are_immutable():
    """Module-level tag lists are shared with the converter - keep them tuples."""
    assert isinstance(SIMPLE_CLOSE_ELEM, tuple)
    assert isinstance(AUTO_CLOSE_DJANGO_ELEM, tuple)
    assert isinstance(NO_AUTO_CLOSE_DJANGO_ELEM, tuple)


def test_ihtml_to_html_failure():
    """Test ihtml_to_html raises instead of returning a blank page."""
    with pytest.raises(TemplateSyntaxError):
        ihtml_to_html("invalid_file", "<div>Test</div>")


if __name__ == "__main__":
    pytest.main()
