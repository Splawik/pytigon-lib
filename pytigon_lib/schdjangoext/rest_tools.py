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
    permission_classes_list_create=[
        IsAuthenticated | TokenHasReadWriteScope,
    ],
    permission_classes_update_destroy=[
        IsAuthenticated | TokenHasReadWriteScope,
    ],
):
    for model_name in dir(models):
        model = getattr(models, model_name)
        model2 = model
        if (
            hasattr(model, "objects")
            and issubclass(model, Model)
            and str(model.__module__) == models.__name__
        ):
            if (not include or model_name in include) and (
                not exclude or not model_name in exclude
            ):

                class _Meta:
                    model = model2
                    fields = "__all__"
                    read_only_fields = ("id",)

                serializer = type(
                    "%sSerializer" % model_name,
                    (serializers.ModelSerializer,),
                    {"Meta": _Meta},
                )

                class _ModelListCreate(generics.ListCreateAPIView):
                    if permission_classes_list_create:
                        permission_classes = permission_classes_list_create
                    queryset = model.objects.all()
                    serializer_class = serializer

                class _ModelRetrieveUpdateDestroy(
                    generics.RetrieveUpdateDestroyAPIView
                ):
                    if permission_classes_update_destroy:
                        permission_classes = permission_classes_update_destroy
                    queryset = model.objects.all()
                    serializer_class = serializer

                urlpatterns.extend(
                    [
                        path(
                            "%ss" % model_name.lower(),
                            _ModelListCreate.as_view(),
                            name="%ss" % model_name.lower(),
                        ),
                        path(
                            "%ss/<int:pk>" % model_name.lower(),
                            _ModelRetrieveUpdateDestroy.as_view(),
                            name="%ss_details" % model_name.lower(),
                        ),
                    ]
                )
