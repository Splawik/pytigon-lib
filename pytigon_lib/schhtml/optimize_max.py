"""Optional PyArrow backed table backend.

This module is used automatically by :func:`pytigon_lib.schhtml.htmlviewer.
tdata_from_html` when PyArrow is installed.  It keeps the ``data`` strings in a
compact columnar array while ``attrs`` and ``children`` stay in flat Python
lists, so that arbitrary Python objects (dictionaries, parsed child nodes, ...)
survive unchanged.

If PyArrow is missing, importing this module raises :class:`ImportError` and
the caller falls back to :mod:`pytigon_lib.schhtml.optimize`, which provides
the same behavior in pure Python.
"""

import pyarrow as pa

from pytigon_lib.schhtml.optimize import (
    OptimizedRow,
    TdView,
    _cell_parts,
)
from pytigon_lib.schhtml.optimize import OptimizedTable as _BaseOptimizedTable

__all__ = ["OptimizedRow", "OptimizedTable", "TdView", "optimize_table"]


class OptimizedTable(_BaseOptimizedTable):
    """PyArrow backed :class:`~pytigon_lib.schhtml.optimize.OptimizedTable`."""

    __slots__ = ("_overrides",)

    def __init__(self, data_column, attrs, children, offsets):
        super().__init__(data_column, attrs, children, offsets)
        self._overrides = {}

    def _get_data(self, pos):
        try:
            return self._overrides[pos]
        except KeyError:
            return self._data[pos].as_py()

    def _set_data(self, pos, value):
        self._overrides[pos] = value


def optimize_table(original_table):
    """Build a PyArrow backed table or return ``None`` when not applicable.

    ``None`` is returned for ``None`` input or when any ``data`` value is not a
    string, because PyArrow would have to coerce it and that would change the
    observable cell value.  The caller then falls back to the pure Python
    backend.
    """
    if original_table is None:
        return None

    data = []
    attrs = []
    children = []
    offsets = [0]

    for row in original_table:
        for cell in row:
            cell_data, cell_attrs, cell_children = _cell_parts(cell)
            if cell_data is not None and not isinstance(cell_data, str):
                return None
            data.append(cell_data)
            attrs.append(cell_attrs)
            children.append(cell_children)
        offsets.append(len(data))

    data_column = pa.array(data, type=pa.string())
    return OptimizedTable(data_column, attrs, children, offsets)
