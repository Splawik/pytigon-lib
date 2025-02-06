from pytigon_lib.schdjangoext.graphql import *

# Pytest tests
import pytest
from django.db import models
from graphene import Schema


class SampleModel(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        app_label = "test_app"


class Query:
    pass


def test_add_graphql_to_class():
    add_graphql_to_class(SampleModel, {"name": ["exact"]}, Query)

    assert hasattr(Query, "test_app__SampleModel")
    assert hasattr(Query, "test_app__SampleModelAll")


def test_add_graphql_to_class_with_invalid_model():
    with pytest.raises(AttributeError):
        add_graphql_to_class(None, {}, Query)


if __name__ == "__main__":
    pytest.main()
