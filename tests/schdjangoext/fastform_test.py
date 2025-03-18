from pytigon_lib.schdjangoext.fastform import *

# Pytest tests
import pytest
from django.core.exceptions import ValidationError



def test_form_from_str():
    form_str = """
    Name::***********************
    Age::000
    Description::_
    """
    form_class = form_from_str(form_str)
    form = form_class()

    assert "name" in form.fields
    assert "age" in form.fields
    assert "description" in form.fields

    assert isinstance(form.fields["name"], forms.CharField)
    assert isinstance(form.fields["age"], forms.IntegerField)
    assert isinstance(form.fields["description"], forms.CharField)

    form = form_class(
        data={"name": "Test", "age": 25, "description": "Test Description"}
    )
    assert form.is_valid()


def test_form_from_str_with_choices():
    form_str = """
    Choose::[option1;option2;option3]
    """
    form_class = form_from_str(form_str)
    form = form_class()

    assert "choose" in form.fields
    assert isinstance(form.fields["choose"], forms.ChoiceField)
    assert form.fields["choose"].choices == [
        ("option1", "option1"),
        ("option2", "option2"),
        ("option3", "option3"),
    ]


def test_form_from_str_with_initial_data():
    form_str = """
    Name::***********************
    """
    form_class = form_from_str(form_str, init_data={"name": "Initial Name"})
    form = form_class()

    assert form.fields["name"].initial == "Initial Name"


def test_form_from_str_with_required_field():
    form_str = """
    Name!::***********************
    """
    form_class = form_from_str(form_str)
    form = form_class(data={})

    assert not form.is_valid()
    assert "name" in form.errors


def test_form_from_str_with_invalid_data():
    form_str = """
    Age::000
    """
    form_class = form_from_str(form_str)
    form = form_class(data={"age": "invalid"})

    assert not form.is_valid()
    assert "age" in form.errors


if __name__ == "__main__":
    pytest.main()
