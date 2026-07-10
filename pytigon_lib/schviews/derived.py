"""Derived object support for schviews generic views."""


class DerivedObjectMixin:
    """Mixin that transparently resolves derived objects via ``get_derived_object``.

    Overrides ``get_object`` so that if the fetched model instance has a
    ``get_derived_object`` method, the derived object is returned and
    ``self.model`` is updated accordingly.
    """

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if hasattr(obj, "get_derived_object"):
            obj2 = obj.get_derived_object({"view": self})
            self.model = type(obj2)
            return obj2
        return obj
