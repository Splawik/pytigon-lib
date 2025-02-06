from graphene import Node
from graphene_django.filter import DjangoFilterConnectionField
from graphene_django.types import DjangoObjectType


def add_graphql_to_class(model, filter_fields, query_class):
    """
    Adds GraphQL schema definitions to a Django model class.

    Args:
        model: The Django model class to which GraphQL schema will be added.
        filter_fields: Fields to be used for filtering in GraphQL queries.
        query_class: The GraphQL query class where the schema will be added.

    Raises:
        AttributeError: If the model does not have the required attributes.
    """

    _model = model
    _filter_fields = filter_fields

    if hasattr(_model._meta, "app_label"):
        app_label = getattr(_model._meta, "app_label")
    else:
        app_label = ""

    try:
        app_label = model._meta.app_label if hasattr(model._meta, "app_label") else ""

        class Meta:
            nonlocal _model, _filter_fields
            model = _model
            interfaces = (Node,)
            filter_fields = _filter_fields

        # Dynamically create a new DjangoObjectType class for the model
        ModelType = type(
            f"{app_label}__{model.__name__}__class",
            (DjangoObjectType,),
            {"Meta": Meta},
        )

        # Add the new type to the query class
        setattr(query_class, f"{app_label}__{model.__name__}", Node.Field(ModelType))
        setattr(
            query_class,
            f"{app_label}__{model.__name__}All",
            DjangoFilterConnectionField(ModelType),
        )

    except AttributeError as e:
        raise AttributeError(f"Model is missing required attributes: {e}")
