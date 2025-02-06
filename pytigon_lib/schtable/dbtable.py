import django.apps.registry
from pytigon_lib.schtable import table
from pytigon_lib.schtools import schjson

__COLMAP__ = {
    "AutoField": "string",
    "SOIntCol": "long",
    "CharField": "string",
    "TextField": "string",
    "BooleanField": "bool",
    "SOFloatCol": "double",
    "SOKeyCol": "long",
    "SOForeignKey": "x",
    "SOEnumCol": "string",
    "SODateTimeCol": "date",
    "DateField": "date",
    "SODecimalCol": "double",
    "SOCurrencyCol": "double",
    "SOBLOBCol": "string",
    "SOPickleCol": "string",
    "SOStringLikeCol": "string",
}

__COLINIT__ = {
    "AutoField": None,
    "SOIntCol": "0",
    "CharField": "",
    "TextField": "",
    "BooleanField": True,
    "SOFloatCol": 0.0,
    "SOKeyCol": None,
    "HiddenForeignKey": None,
    "ForeignKey": None,
    "SOEnumCol": "",
    "SODateTimeCol": "2000-01-01",
    "DateField": "2000-01-01",
    "SODecimalCol": 0.0,
    "SOCurrencyCol": 0.0,
    "SOBLOBCol": "",
    "SOPickleCol": "",
    "SOStringLikeCol": "",
}

__COLSIZE__ = {
    "AutoField": 9,
    "SOIntCol": 9,
    "CharField": 0,
    "TextField": 0,
    "BooleanField": 1,
    "SOFloatCol": 12,
    "SOKeyCol": 25,
    "ForeignKey": 25,
    "HiddenForeignKey": 25,
    "SOEnumCol": 25,
    "SODateTimeCol": 18,
    "SODateCol": 10,
    "SODecimalCol": 12,
    "SOCurrencyCol": 12,
    "SOBLOBCol": 9,
    "SOPickleCol": 10,
    "SOStringLikeCol": 0,
    "DateField": 10,
}


class DbTable(table.Table):
    def __init__(self, app, tab):
        self.auto_cols = []
        self.foreign_key_parm = {}
        self.app = app
        self.tab = tab

        self.tab_conw = {
            "long": self.conw_long,
            "string": self.conw_none,
            "double": self.conw_float,
            "bool": self.conw_bool,
            "choice": self.conw_none,
            "x": self.conw_x,
        }

        self.model_class = django.apps.registry.apps.get_model(app, tab)
        self.col_length = self._get_col_length()
        self.col_names = self._get_col_names()
        self.col_types = self._get_col_types()
        self.default_rec = self._get_default_rec()
        self.query = None

    def conw_long(self, value):
        return int(value) if value else None

    def conw_none(self, value):
        return value

    def conw_float(self, value):
        return float(value) if value else None

    def conw_bool(self, value):
        return bool(value) if value else None

    def conw_x(self, value):
        return value.GetStringRepr() if value else "0"

    def _get_col_names(self):
        return [col.verbose_name or col.name for col in self.model_class._meta.fields]

    def _get_default_rec(self):
        return [
            __COLINIT__.get(col.__class__.__name__)
            for col in self.model_class._meta.fields
        ]

    def _get_col_types(self):
        col_types = []
        for col in self.model_class._meta.fields:
            if type(col).__name__ in ("ForeignKey", "HiddenForeignKey"):
                pos = f"x:/{self.app}/table/{self.tab}/{col.name}/dict/"
                if col.name[:-2] in self.foreign_key_parm:
                    pos += "|" + self.foreign_key_parm
                col_types.append(pos)
            else:
                col_types.append(
                    f"y:{schjson.dumps(col.choices)}"
                    if col.choices
                    else __COLMAP__.get(col.__class__.__name__, "string")
                )
        return col_types

    def _get_col_length(self):
        col_lengths = []
        for col in self.model_class._meta.fields:
            size = __COLSIZE__.get(col.__class__.__name__, 25)
            if size == 0:
                if col.choices:
                    size = max(len(choice[1]) for choice in col.choices)
                else:
                    size = col.max_length or 25
            col_lengths.append(size)
        return col_lengths[1:]

    def _set_sort(self, objects, sort):
        sortobj = objects
        for item in sort.split(","):
            reverse = item.startswith("-")
            item = item[1:] if reverse else item
            for col in self.model_class._meta.fields:
                colname = col.verbose_name or col.name
                if item == colname:
                    sort_field = f"-{col.name}" if reverse else col.name
                    sortobj = sortobj.order_by(sort_field)
        return sortobj

    def page(self, nr, sort=None, value=None):
        data = (
            self.model_class.simple_query(value)
            if value and hasattr(self.model_class, "simple_query")
            else self.model_class.objects.all()
        )
        if sort:
            data = self._set_sort(data, sort)
        data = data[nr * 256 : (nr + 1) * 256]
        tab = []
        for rec in data:
            row = []
            for field in self.model_class._meta.fields:
                value = field.value_from_object(rec)
                if field.choices:
                    value = (
                        f"{value}:{dict(field.choices).get(value, '')}"
                        if value in dict(field.choices)
                        else ""
                    )
                elif type(field).__name__ in ("ForeignKey", "HiddenForeignKey"):
                    value2 = getattr(rec, field.name)
                    value = f"{value2.id}:{value2}" if value2 else "0"
                row.append(value)
            tab.append(row)
        return tab

    def rec_as_str(self, nr):
        try:
            obj = self.model_class.objects.get(id=nr)
            return str(obj)
        except self.model_class.DoesNotExist:
            return ""

    def count(self, v):
        return self.model_class.objects.count()

    def insert_rec(self, rec):
        obj = self.model_class()
        for i, field in enumerate(self.model_class._meta.fields[1:], start=1):
            value = rec[i]
            if field.choices:
                value = value.split(":")[0]
            if type(field).__name__ in ("ForeignKey", "HiddenForeignKey"):
                value = (
                    field.rel.to.objects.get(id=int(value.split(":")[0]))
                    if value
                    else None
                )
            field.save_form_data(obj, value)
        obj.save()

    def update_rec(self, rec):
        try:
            obj = self.model_class.objects.get(id=rec[0])
            for i, field in enumerate(self.model_class._meta.fields[1:], start=1):
                value = rec[i]
                if field.choices:
                    value = value.split(":")[0]
                if type(field).__name__ in ("ForeignKey", "HiddenForeignKey"):
                    value = (
                        field.rel.to.objects.get(id=int(value.split(":")[0]))
                        if value
                        else None
                    )
                field.save_form_data(obj, value)
            obj.save()
        except self.model_class.DoesNotExist:
            pass

    def delete_rec(self, nr):
        try:
            obj = self.model_class.objects.get(id=nr)
            obj.delete()
        except self.model_class.DoesNotExist:
            pass

    def auto(self, col_name, col_names, rec):
        pass
