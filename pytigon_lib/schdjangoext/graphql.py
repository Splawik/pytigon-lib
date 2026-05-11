"""GraphQL integration helpers for Django models.

Provides utilities to dynamically generate GraphQL types and
attach them to a query class.
"""

from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType


def add_graphql_to_class(model, filter_fields, query_class):
    """Dynamically add GraphQL type and fields for a Django model.

    Creates a :class:`DjangoObjectType` subclass for the given
    ``model`` and attaches both a single-node field and an all-items
    filter field to ``query_class``.

    Args:
        model: The Django model class.
        filter_fields: Mapping of filterable fields for GraphQL.
        query_class: The GraphQL query class to extend.

    Raises:
        AttributeError: If ``model`` lacks a ``_meta`` attribute.
    """
    # Safely extract the app_label
    app_label = getattr(getattr(model, "_meta", None), "app_label", "")
    if not app_label:
        raise AttributeError(
            f"Model '{getattr(model, '__name__', model)}' has no '_meta.app_label'"
        )

    _model = model
    _filter_fields = filter_fields

    class Meta:
        nonlocal _model, _filter_fields
        model = _model
        interfaces = (Node,)
        filter_fields = _filter_fields

    # Dynamically create a new DjangoObjectType class for the model
    type_name = f"{app_label}__{model.__name__}__class"
    ModelType = type(type_name, (DjangoObjectType,), {"Meta": Meta})

    # Add single-node and all-items fields to the query class
    setattr(query_class, f"{app_label}__{model.__name__}", Node.Field(ModelType))
    setattr(
        query_class,
        f"{app_label}__{model.__name__}All",
        DjangoFilterConnectionField(ModelType),
    )
