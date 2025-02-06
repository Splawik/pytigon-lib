from pytigon_lib.schdjangoext.spreadsheet_render import *

# Pytest tests
import pytest
from django.template import Context


def test_oo_dict():
    """Test the oo_dict function."""
    template_name = "test_template.odt"
    result = oo_dict(template_name)
    assert isinstance(result, list)


def test_render_odf():
    """Test the render_odf function."""
    template_name = "test_template.odt"
    context_instance = Context({"test_var": "test_value"})
    result = render_odf(template_name, context_instance)
    assert isinstance(result, tuple)


def test_render_to_response_odf():
    """Test the render_to_response_odf function."""
    template_name = "test_template.odt"
    context_instance = Context({"test_var": "test_value"})
    response = render_to_response_odf(template_name, context_instance)
    assert isinstance(response, HttpResponse)


def test_render_ooxml():
    """Test the render_ooxml function."""
    template_name = "test_template.xlsx"
    context_instance = Context({"test_var": "test_value"})
    result = render_ooxml(template_name, context_instance)
    assert isinstance(result, tuple)


def test_render_to_response_ooxml():
    """Test the render_to_response_ooxml function."""
    template_name = "test_template.xlsx"
    context_instance = Context({"test_var": "test_value"})
    response = render_to_response_ooxml(template_name, context_instance)
    assert isinstance(response, HttpResponse)
