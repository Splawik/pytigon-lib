from .htmltools import superstrip
import re


def comment_remover(text):
    """Remove comments from the given text."""

    def replacer(match):
        s = match.group(0)
        return "" if s.startswith("/") else s

    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE,
    )
    return re.sub(pattern, replacer, text)


class CssPos:
    """Represents a CSS position with attributes and parent relationships."""

    def __init__(self, line, attrs):
        self.tag = superstrip(line[-1])
        self.parents = {}
        self.attrs = attrs if len(line) == 1 else {}
        if len(line) > 1:
            parent = CssPos(line[:-1], attrs)
            self.parents[parent.key()] = parent

    def key(self):
        """Return the key for this CSS position."""
        return self.tag

    def _extend_dict(self, dest, source):
        """Extend the destination dictionary with the source dictionary."""
        dest.update(source)

    def extend(self, line, attrs):
        """Extend the CSS position with additional attributes."""
        if line:
            key_main = line[-1]
            if key_main in self.parents:
                self.parents[key_main].extend(line[:-1], attrs)
            else:
                parent = CssPos(line, attrs)
                self.parents[parent.key()] = parent
        else:
            self.attrs.update(attrs)

    def _get_dict_from_parent(self, key, ret_attrs, obj):
        """Get attributes from a parent CSS position."""
        if key in self.parents and obj.get_parent():
            self._extend_dict(ret_attrs, self.parents[key].get_dict(obj.get_parent()))

    def get_dict(self, obj):
        """Get the combined attributes for the given object."""
        ret_attrs = self.attrs.copy()
        if obj:
            self._get_dict_from_parent(obj.get_tag(), ret_attrs, obj)
            if obj.get_cls():
                self._get_dict_from_parent("." + obj.get_cls(), ret_attrs, obj)
                self._get_dict_from_parent(
                    obj.get_tag() + "." + obj.get_cls(), ret_attrs, obj
                )
            if obj.get_id():
                self._get_dict_from_parent("#" + obj.get_id(), ret_attrs, obj)
                self._get_dict_from_parent(
                    obj.get_tag() + "." + obj.get_id(), ret_attrs, obj
                )
        return ret_attrs

    def test_print(self, indent):
        """Print the CSS position for testing purposes."""
        tab = indent * " "
        print(f"{tab}{self.key()}:")
        print(f"{tab}attrs:")
        for key, value in self.attrs.items():
            print(f"{tab}    {key}: {value}")
        print(f"{tab}parents:")
        for key, parent in self.parents.items():
            print(f"{tab}    key:")
            parent.test_print(indent + 8)


class Css:
    """Represents a CSS stylesheet."""

    def __init__(self):
        self.csspos_dict = {}
        self._act_dict = {}
        self._act_keys = []

    def _append_keys(self):
        """Append the current keys to the CSS position dictionary."""
        if self._act_keys:
            for pos in self._act_keys:
                lastkey = pos[-1]
                if lastkey in self.csspos_dict:
                    self.csspos_dict[lastkey].extend(pos[:-1], self._act_dict)
                else:
                    self.csspos_dict[lastkey] = CssPos(pos, self._act_dict)
        self._act_keys = []
        self._act_dict = {}

    def parse_indent_str(self, s):
        """Parse a string with indentation-based CSS."""
        for line in s.splitlines():
            if not line:
                continue
            indent = line[0] == " "
            line = superstrip(line.split("//")[0])
            if not line:
                continue
            if indent:
                key, *value = line.split(":")
                self._act_dict[key.strip()] = value[0].strip() if value else "0"
            else:
                if self._act_keys:
                    self._append_keys()
                self._act_keys = [
                    pos.strip().lower().split() for pos in line.split(",")
                ]
                self._act_dict = {}
        if self._act_keys:
            self._append_keys()

    def _strip_list(self, lst):
        """Strip whitespace from each element in the list."""
        return [item.strip() for item in lst]

    def _handle_section(self, section):
        """Handle a single CSS section."""
        selector, *content = section.split("{")
        if not content:
            return
        self._act_keys = [
            pos.strip().lower().split() for pos in superstrip(selector).split(",")
        ]
        self._act_dict = {}
        for prop in content[0].split(";"):
            key, *value = self._strip_list(prop.split(":"))
            if key:
                self._act_dict[key] = value[0] if value else "0"
        if self._act_keys:
            self._append_keys()

    def parse_str(self, s):
        """Parse a CSS string."""
        s2 = comment_remover(s)
        for section in superstrip(s2).split("}"):
            self._handle_section(section)

    def test_print(self):
        """Print the CSS for testing purposes."""
        tmp = CssPos([""], {})
        tmp.parents = self.csspos_dict
        tmp.test_print(0)

    def get_dict(self, obj):
        """Get the combined attributes for the given object."""
        tmp = CssPos([""], {})
        tmp.parents = self.csspos_dict
        return tmp.get_dict(obj)
