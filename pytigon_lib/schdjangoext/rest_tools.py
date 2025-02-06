from django.urls import path
from django.db.models import Model
from rest_framework import serializers, generics
from rest_framework.permissions import IsAuthenticated
from oauth2_provider.contrib.rest_framework import TokenHasReadWriteScope


def create_api_for_models(
    models,
    urlpatterns,
    include=None,
    exclude=None,
    permission_classes_list_create=[IsAuthenticated | TokenHasReadWriteScope],
    permission_classes_update_destroy=[IsAuthenticated | TokenHasReadWriteScope],
):
    """
    Dynamically creates API endpoints for Django models.

    Args:
        models: Module containing Django models.
        urlpatterns: List to which the generated URL patterns will be added.
        include: List of model names to include (optional).
        exclude: List of model names to exclude (optional).
        permission_classes_list_create: Permissions for list/create views.
        permission_classes_update_destroy: Permissions for update/destroy views.
    """
    for model_name in dir(models):
        model = getattr(models, model_name)
        model2 = model
        # Check if the attribute is a Django model and belongs to the specified module
        if (
            hasattr(model, "objects")
            and issubclass(model, Model)
            and str(model.__module__) == models.__name__
        ):
            # Apply include/exclude filters
            if (include and model_name not in include) or (
                exclude and model_name in exclude
            ):
                continue

            # Define Meta class for the serializer
            class _Meta:
                model = model2
                fields = "__all__"
                read_only_fields = ("id",)

            # Create a serializer for the model
            serializer = type(
                f"{model_name}Serializer",
                (serializers.ModelSerializer,),
                {"Meta": _Meta},
            )

            # Define ListCreateAPIView for the model
            class _ModelListCreate(generics.ListCreateAPIView):
                permission_classes = permission_classes_list_create
                queryset = model.objects.all()
                serializer_class = serializer

            # Define RetrieveUpdateDestroyAPIView for the model
            class _ModelRetrieveUpdateDestroy(generics.RetrieveUpdateDestroyAPIView):
                permission_classes = permission_classes_update_destroy
                queryset = model.objects.all()
                serializer_class = serializer

            # Add URL patterns for the model
            urlpatterns.extend(
                [
                    path(
                        f"{model_name.lower()}s/",
                        _ModelListCreate.as_view(),
                        name=f"{model_name.lower()}s",
                    ),
                    path(
                        f"{model_name.lower()}s/<int:pk>/",
                        _ModelRetrieveUpdateDestroy.as_view(),
                        name=f"{model_name.lower()}s_details",
                    ),
                ]
            )
