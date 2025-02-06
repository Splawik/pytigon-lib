"""Module contains many additional db models."""

import sys
from typing import Any, Dict, List, Optional, Type

from django.db import models
from django import forms
from django.core import serializers
from django.contrib.contenttypes.models import ContentType

from pytigon_lib.schtools.schjson import ComplexEncoder, ComplexDecoder
from pytigon_lib.schdjangoext.fastform import form_from_str


class CallProxy:
    """Proxy class to call methods dynamically based on parameters."""

    def __init__(self, obj: Any, parameters: str):
        self.obj = obj
        x = parameters.split("__")
        self.fun = getattr(obj, x[0])
        self.parameters = x[1:] if len(x) > 1 else None

    def call(self, *args: Any) -> Any:
        """Call the method with the provided arguments."""
        if self.parameters:
            return self.fun(*(self.parameters + args))
        return self.fun(*args)


class JSONModel(models.Model):
    """Abstract model to handle JSON data fields."""

    class Meta:
        abstract = True

    jsondata = models.JSONField(
        "Json data",
        encoder=ComplexEncoder,
        decoder=ComplexDecoder,
        null=True,
        blank=True,
        editable=False,
    )

    def __getattribute__(self, name: str) -> Any:
        """Override to handle JSON data access."""
        if name.startswith("json_"):
            if self.jsondata and name[5:] in self.jsondata:
                return self.jsondata[name[5:]]
            return None
        elif name.startswith("call__"):
            return CallProxy(self, name[6:])
        return super().__getattribute__(name)

    def __setattr__(self, name: str, value: Any) -> None:
        """Override to handle JSON data assignment."""
        if name.startswith("json_"):
            if self.jsondata:
                self.jsondata[name[5:]] = value
            else:
                self.jsondata = {name[5:]: value}
            return
        super().__setattr__(name, value)

    def get_json_data(self) -> Dict[str, Any]:
        """Return the JSON data associated with the model."""
        return self.jsondata if self.jsondata else {}

    def get_form(
        self,
        view: Any,
        request: Any,
        form_class: Type[forms.Form],
        adding: bool = False,
    ) -> forms.Form:
        """Generate a form based on JSON data."""
        data = self.get_json_data()
        if hasattr(self, "get_form_source"):
            txt = self.get_form_source()
            if txt:
                form_class2 = form_from_str(
                    txt,
                    init_data=data if data else {},
                    base_form_class=form_class,
                    prefix="json_",
                )
                return view.get_form(form_class2)
        elif data:

            class form_class2(form_class):
                def __init__(self, *args: Any, **kwargs: Any):
                    super().__init__(*args, **kwargs)
                    for key, value in data.items():
                        self.fields[f"json_{key}"] = forms.CharField(
                            label=key, initial=value
                        )

            return view.get_form(form_class2)
        return view.get_form(form_class)

    def get_derived_object(self, param: Any = None) -> Any:
        """Return the derived object."""
        return self

    def set_field_value(
        self, field_name: str, attr_name: str, value: Any
    ) -> Optional[Any]:
        """Set a field's attribute value."""
        for f in self._meta.fields:
            if f.name == field_name:
                setattr(f, attr_name, value)
                return f
        return None


class TreeModel(JSONModel):
    """Abstract model for tree-like structures."""

    class Meta:
        abstract = True


ASSOCIATED_MODEL_CACHE: Dict[str, Any] = {}


class AssociatedModel(models.Model):
    """Abstract model to handle associations with other models."""

    class Meta:
        abstract = True

    application = models.CharField(
        "Application",
        null=False,
        blank=False,
        editable=False,
        db_index=True,
        max_length=64,
    )
    table = models.CharField(
        "Table",
        null=False,
        blank=False,
        editable=False,
        default="default",
        db_index=True,
        max_length=64,
    )
    group = models.CharField(
        "Group",
        null=True,
        blank=True,
        editable=False,
        default="default",
        db_index=True,
        max_length=64,
    )
    parent_id = models.IntegerField(
        "Parent id",
        null=True,
        blank=True,
        editable=False,
        db_index=True,
    )

    def get_associated_model(self) -> Optional[Type[models.Model]]:
        """Retrieve the associated model class."""
        global ASSOCIATED_MODEL_CACHE
        key = f"{self.application.lower()}/{self.table.lower()}"
        if key in ASSOCIATED_MODEL_CACHE:
            return ASSOCIATED_MODEL_CACHE[key]
        model_obj = ContentType.objects.filter(
            app_label=self.application.lower(), model=self.table.lower()
        ).first()
        if model_obj:
            model_class = model_obj.model_class()
            ASSOCIATED_MODEL_CACHE[key] = model_class
            return model_class
        return None

    def get_associated_obj(self) -> Optional[models.Model]:
        """Retrieve the associated object."""
        model = self.get_associated_model()
        return model.objects.filter(pk=self.parent_id).first() if model else None

    def get_associated_obj_to_parent(self) -> Optional[models.Model]:
        """Retrieve the associated object's parent."""
        model = self.get_associated_model()
        if model:
            parent = model.objects.filter(pk=self.parent_id).first()
            if parent and hasattr(parent, "get_associated_obj"):
                return parent.get_associated_obj()
        return None

    def init_new(
        self, request: Any, view: Any, value: Optional[str] = None
    ) -> Dict[str, Any]:
        """Initialize a new associated model instance."""
        if value:
            x = value.split("__")
            if len(x) == 4:
                app, tbl, id, grp = x
            elif len(x) == 3:
                app, tbl, id = x
                grp = "default"
            if app:
                return {"application": app, "table": tbl, "parent_id": id, "group": grp}
        return {
            "application": "default",
            "table": "default",
            "parent_id": 0,
            "group": "default",
        }

    @classmethod
    def filter(
        cls, value: Optional[str], view: Any = None, request: Any = None
    ) -> models.QuerySet:
        """Filter the associated model instances."""
        if value:
            x = value.split("__")
            if len(x) == 4:
                app, tbl, id, grp = x
            elif len(x) == 3:
                app, tbl, id = x
                grp = "default"
            if app:
                return cls.objects.filter(
                    application=app, table=tbl, parent_id=id, group=grp
                )
        return cls.objects.all()


class AssociatedJSONModel(AssociatedModel, JSONModel):
    """Abstract model combining JSON and associated model features."""

    class Meta:
        abstract = True


def standard_table_action(
    cls: Type[models.Model],
    list_view: Any,
    request: Any,
    data: Dict[str, Any],
    operations: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Handle standard table actions like copy, paste, and delete."""
    if "action" in data and data["action"] in operations:
        if data["action"] == "copy":
            if "pk" in request.GET:
                x = request.GET["pks"].split(",")
                x2 = [int(pos) for pos in x]
                return serializers.serialize(
                    "json", list_view.get_queryset().filter(pk__in=x2)
                )
            return serializers.serialize("json", list_view.get_queryset())
        if data["action"] == "paste":
            if "data" in data:
                data2 = data["data"]
                for obj in data2:
                    obj2 = cls()
                    for key, value in obj["fields"].items():
                        if key not in ("id", "pk"):
                            if key == "parent" and "parent_pk" in list_view.kwargs:
                                setattr(
                                    obj2, "parent_id", list_view.kwargs["parent_pk"]
                                )
                            else:
                                setattr(obj2, key, value)
                    obj2.save()
            return {"success": 1}
        if data["action"] == "delete":
            if "pks" in request.GET:
                x = request.GET["pks"].split(",")
                x2 = [int(pos) for pos in x]
                if x2:
                    list_view.get_queryset().filter(pk__in=x2).delete()
                return []
    return None


def get_form(
    obj: models.Model,
    fields_list: Optional[List[str]] = None,
    widgets_dict: Optional[Dict[str, Any]] = None,
) -> Type[forms.ModelForm]:
    """Generate a ModelForm for the given object."""

    class _Form(forms.ModelForm):
        class Meta:
            model = obj.__class__
            fields = fields_list if fields_list else "__all__"
            widgets = widgets_dict if widgets_dict else {}

    return _Form


def extend_class(main: Type[Any], base: Type[Any]) -> None:
    """Extend a class with a base class."""
    if not any(
        cmd in sys.argv
        for cmd in ["makemigrations", "makeallmigrations", "exporttolocaldb"]
    ):
        main.__bases__ = (base,) + main.__bases__


if any(
    cmd in sys.argv
    for cmd in ["makemigrations", "makeallmigrations", "exporttolocaldb", "migrate"]
):

    def OverwritableCallable(func: Any) -> Any:
        """Dummy decorator for migration commands."""

        def __none__(fun: Any) -> None:
            pass

        func.set_function = __none__
        return func

else:

    class OverwritableCallable:
        """Callable class that allows function overwriting."""

        def __init__(self, func: Any):
            self.func = func

        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            return self.func(*args, **kwargs)

        def set_function(self, func: Any) -> None:
            self.func = func
