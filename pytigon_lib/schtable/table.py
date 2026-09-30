import logging
from functools import cmp_to_key

from pytigon_lib.schtools import schjson

logger = logging.getLogger(__name__)

#: Returned to HTTP clients instead of the raw exception text, which can leak
#: internal file system paths and SQL fragments.
GENERIC_ERROR = "Table operation failed"

# Command constants
CMD_INFO = 1
CMD_PAGE = 2
CMD_COUNT = 3
CMD_SYNC = 4
CMD_AUTO = 5
CMD_RECASSTR = 6
CMD_EXEC = 7


class Table:
    """Base class for server table interface."""

    def __init__(self):
        """Initialize table with default columns and types."""
        self.auto_cols = []
        self.col_length = [0]
        self.col_names = ["ID"]
        self.col_types = ["int"]
        self.default_rec = [0]

    def _info(self):
        """Return table metadata as JSON."""
        return schjson.dumps(
            {
                "auto_cols": self.auto_cols,
                "col_length": self.col_length,
                "col_names": self.col_names,
                "col_types": self.col_types,
                "default_rec": self.default_rec,
            }
        )

    def _page(self, nr, sort=None, value=None):
        """Return a page of records as JSON."""
        return schjson.dumps({"page": self.page(nr, sort, value)})

    def _rec_as_str(self, nr):
        """Return a record as a string in JSON format."""
        return schjson.dumps({"recasstr": self.rec_as_str(nr)})

    def _count(self, value=None):
        """Return the count of records as JSON."""
        return schjson.dumps({"count": self.count(value)})

    def _sync(self, update, insert, delete):
        """Synchronize records with the server."""
        try:
            for rec in update:
                self.update_rec(rec)
            for nr in delete:
                self.delete_rec(nr)
            for rec in insert:
                self.insert_rec(rec)
            return "OK"
        except Exception:
            logger.exception("Table synchronize failed")
            return schjson.dumps({"error": GENERIC_ERROR})

    def _auto(self, col_name, col_names, rec):
        """Handle auto-column logic and return the result as JSON."""
        return schjson.dumps({"rec": self.auto(col_name, col_names, rec)})

    def _exec(self, value=None):
        """Execute a command and return the result."""
        try:
            ret = self.exec_command(value)
            return schjson.dumps(ret) if isinstance(ret, dict) else ret
        except Exception:
            logger.exception("Table command execution failed")
            return schjson.dumps({"error": GENERIC_ERROR})

    def page(self, nr, sort=None, value=None):
        """Return a page of records."""
        raise NotImplementedError

    def count(self, value=None):
        """Return the count of records."""
        raise NotImplementedError

    def rec_as_str(self, nr):
        """Return a record as a string."""
        raise NotImplementedError

    def insert_rec(self, rec):
        """Insert a record."""
        raise NotImplementedError

    def update_rec(self, rec):
        """Update a record."""
        raise NotImplementedError

    def delete_rec(self, nr):
        """Delete a record."""
        raise NotImplementedError

    def auto(self, col_name, col_names, rec):
        """Handle auto-column logic."""
        raise NotImplementedError

    def exec_command(self, value):
        """Execute a command."""
        raise NotImplementedError

    def command(self, cmd_dict):
        """Handle a command based on the command dictionary."""
        if not isinstance(cmd_dict, dict):
            logger.warning("Ignoring table command of unexpected type: %r", type(cmd_dict))
            return None
        try:
            cmd = int(cmd_dict.get("cmd", CMD_PAGE))
        except (TypeError, ValueError):
            cmd = CMD_PAGE
        value = cmd_dict.get("value")
        nr = cmd_dict.get("nr", 0)
        sort = cmd_dict.get("sort")

        if cmd == CMD_INFO:
            return self._info()
        elif cmd == CMD_PAGE:
            return self._page(nr, sort, value)
        elif cmd == CMD_COUNT:
            return self._count(value)
        elif cmd == CMD_SYNC:
            return self._sync(
                schjson.loads(cmd_dict.get("update") or "[]"),
                schjson.loads(cmd_dict.get("insert") or "[]"),
                schjson.loads(cmd_dict.get("delete") or "[]"),
            )
        elif cmd == CMD_AUTO:
            col_name = cmd_dict.get("col_name")
            col_names = cmd_dict.get("col_names")
            if not col_name or not col_names:
                logger.warning("Ignoring table auto command without col_name/col_names")
                return None
            return self._auto(col_name, col_names, cmd_dict.get("rec"))
        elif cmd == CMD_RECASSTR:
            try:
                nr = int(cmd_dict.get("nr"))
            except (TypeError, ValueError):
                logger.warning("Ignoring recasstr command with invalid nr: %r", cmd_dict.get("nr"))
                return None
            return self._rec_as_str(nr)
        elif cmd == CMD_EXEC:
            return self._exec(value)
        else:
            return None


def str_cmp(x, y, ts):
    """Compare two strings based on the given sorting criteria."""
    (id, s) = ts[0]
    if x[id] > y[id]:
        return s
    if x[id] < y[id]:
        return -s
    if len(ts) > 1:
        return str_cmp(x, y, ts[1:])
    return 0


class TablePy(Table):
    """Python implementation of the Table class."""

    def __init__(self, table, col_names, col_typ, col_length, default_rec):
        """Initialize the table with data and metadata."""
        self.tab = table
        self.auto_cols = []
        self.col_length = [0] + col_length
        self.col_names = ["ID"] + col_names
        self.col_types = ["int"] + col_typ
        self.default_rec = [0] + default_rec

    def page(self, nr, sort=None, value=None):
        """Return a page of records."""
        tab = []
        tab2 = self.tab[nr * 256 : (nr + 1) * 256]
        for i, rec in enumerate(tab2):
            tab.append([nr * 256 + i] + rec)

        if sort:
            s = sort.split(",")
            ts = []
            for pos in s:
                if pos:
                    id = self.col_names.index(pos[1:] if pos[0] == "-" else pos)
                    ss = -1 if pos[0] == "-" else 1
                    ts.append((id, ss))
            tab.sort(key=cmp_to_key(lambda x, y: str_cmp(x, y, ts)))

        return tab

    def count(self, value=None):
        """Return the count of records."""
        return len(self.tab)

    def insert_rec(self, rec):
        """Insert a record."""
        self.tab.append(rec[1:])

    def update_rec(self, rec):
        """Update a record."""
        self.tab[rec[0]] = rec[1:]

    def delete_rec(self, nr):
        """Delete a record."""
        self.tab.pop(nr)

    def auto(self, col_name, col_names, rec):
        """Handle auto-column logic."""
        pass
