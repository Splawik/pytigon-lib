"""Memory-optimized, behavior-preserving table containers.

The optimized table replaces the original list-of-lists of :class:`Td`
objects with three flat lists (``data``, ``attrs`` and ``children``) plus a
small offsets array.  Cell and row views are created on demand, so the per
cell :class:`Td` instances and the per row lists are not kept in memory.

The public access pattern is unchanged::

    table[row][col].data
    table[row][col].attrs
    table[row][col].children

Integer and slice indexing, negative indices, iteration, ``len()`` and item
assignment keep working like they do for the original list-of-lists table.
"""

from pytigon_lib.schhtml.htmltools import Td


class TdView(Td):
    """A :class:`Td` compatible cell view.

    When created through :func:`optimize_table` the view is backed by the
    owning table and reads/writes are delegated to the flat storage, so
    ``cell.data = value`` behaves exactly like mutating the original cell.
    It can also be created directly with plain values, matching the historical
    ``TdView(data, attrs, children)`` constructor.
    """

    __slots__ = ("_attrs", "_children", "_data", "_pos", "_table")

    def __init__(
        self,
        data=None,
        attrs=None,
        children=None,
        table=None,
        pos=-1,
    ):
        self._table = table
        self._pos = pos
        self._data = data
        self._attrs = attrs if attrs is not None else {}
        self._children = children

    @property
    def data(self):
        if self._table is None:
            return self._data
        return self._table._get_data(self._pos)

    @data.setter
    def data(self, value):
        if self._table is None:
            self._data = value
        else:
            self._table._set_data(self._pos, value)

    @property
    def attrs(self):
        if self._table is None:
            return self._attrs
        return self._table._attrs[self._pos]

    @attrs.setter
    def attrs(self, value):
        if self._table is None:
            self._attrs = value
        else:
            self._table._attrs[self._pos] = value

    @property
    def children(self):
        if self._table is None:
            return self._children
        return self._table._children[self._pos]

    @children.setter
    def children(self, value):
        if self._table is None:
            self._children = value
        else:
            self._table._children[self._pos] = value


class OptimizedRow:
    """A single row view over the flat storage of :class:`OptimizedTable`."""

    __slots__ = ("_row", "_table")

    def __init__(self, table, row):
        self._table = table
        self._row = row

    @property
    def num_cols(self):
        offsets = self._table._offsets
        return offsets[self._row + 1] - offsets[self._row]

    def _bounds(self):
        offsets = self._table._offsets
        return offsets[self._row], offsets[self._row + 1]

    def __getitem__(self, col):
        start, stop = self._bounds()
        count = stop - start
        if isinstance(col, slice):
            return [TdView(table=self._table, pos=start + i) for i in range(*col.indices(count))]
        if col < 0:
            col += count
        if not (0 <= col < count):
            raise IndexError("Column index out of range.")
        return TdView(table=self._table, pos=start + col)

    def __setitem__(self, col, value):
        start, stop = self._bounds()
        count = stop - start
        if col < 0:
            col += count
        if not (0 <= col < count):
            raise IndexError("Column index out of range.")
        self._table._set_cell(start + col, value)

    def __iter__(self):
        start, stop = self._bounds()
        return (TdView(table=self._table, pos=i) for i in range(start, stop))

    def __len__(self):
        start, stop = self._bounds()
        return stop - start

    def __repr__(self):
        return repr([TdView(table=self._table, pos=i) for i in self.__iter__()])


class OptimizedTable:
    """Flat, memory-efficient replacement for a list of rows of :class:`Td`."""

    __slots__ = ("_attrs", "_children", "_data", "_offsets", "num_cols", "num_rows")

    def __init__(self, data, attrs, children, offsets):
        self._data = data
        self._attrs = attrs
        self._children = children
        self._offsets = offsets
        self.num_rows = len(offsets) - 1
        self.num_cols = max(
            (offsets[i + 1] - offsets[i] for i in range(self.num_rows)),
            default=0,
        )

    def _get_data(self, pos):
        return self._data[pos]

    def _set_data(self, pos, value):
        self._data[pos] = value

    def _set_cell(self, pos, value):
        if hasattr(value, "data") and (hasattr(value, "attrs") or hasattr(value, "children")):
            self._set_data(pos, value.data)
            self._attrs[pos] = getattr(value, "attrs", {})
            self._children[pos] = getattr(value, "children", None)
        else:
            self._set_data(pos, value)

    def __getitem__(self, row):
        if isinstance(row, slice):
            start, stop, step = row.indices(self.num_rows)
            return [OptimizedRow(self, i) for i in range(start, stop, step)]
        if row < 0:
            row += self.num_rows
        if not (0 <= row < self.num_rows):
            raise IndexError("Row index out of range.")
        return OptimizedRow(self, row)

    def __iter__(self):
        return (OptimizedRow(self, i) for i in range(self.num_rows))

    def __len__(self):
        return self.num_rows


def _cell_parts(cell):
    """Return ``(data, attrs, children)`` for a cell like object."""
    data = getattr(cell, "data", cell)
    attrs = getattr(cell, "attrs", None)
    children = getattr(cell, "children", None)
    return data, attrs if attrs is not None else {}, children


def optimize_table(original_table):
    """Transform a list of rows of :class:`Td` into an :class:`OptimizedTable`.

    The original cell values are kept by reference (``data`` objects, ``attrs``
    dictionaries and ``children`` objects are not copied or converted), so the
    observable behavior is identical to the plain table.
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
            data.append(cell_data)
            attrs.append(cell_attrs)
            children.append(cell_children)
        offsets.append(len(data))

    return OptimizedTable(data, attrs, children, offsets)
