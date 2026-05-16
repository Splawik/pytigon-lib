from django.conf import settings
from django.template import Template
from django.utils.html import escape
from django.utils.translation import gettext_lazy as _

STANDARD_ACTIONS = {
    "default": {
        "target": "_parent",
        "class": "btn {{btn_size}} btn-primary shadow-none",
        "class_in_menu": "",
        "attrs": "data-role='button' data-inline='true' data-mini='true'",
        "attrs_in_menu": "",
        "url": "{ap}table/{table_name}/{id}/action/{action}/",
    },
    "action": {
        "target": "inline_edit",
        "attrs": "data-inline-position='^tr, .tr:after'",
        "attrs_in_menu": "data-inline-position='^tr, .tr:after'",
    },
    "new_row": {
        "target": "popup_edit",
        "class": "btn {{btn_size}} btn-light shadow-none edit new-row",
        "attrs": "data-inline-position='^tr, .tr:after'",
        "attrs_in_menu": "data-inline-position='^tr, .tr:after'",
    },
    "edit": {
        "target": "popup_edit",
        "title": _("Update"),
        "class": "btn {{btn_size}} btn-primary shadow-none edit",
        "attrs": "data-role='button' data-inline='true' data-mini='true' "
        "data-inline-position='^tr, .tr:after'",
        "url": "{tp}{id}/{action}/",
        "icon": "edit fa-pencil fa-lg",
        "attrs_in_menu": "data-inline-position='^tr, .tr:after'",
    },
    "delete": {
        "target": "popup_delete",
        "title": _("Delete"),
        "class": "popup_delete btn {{btn_size}} btn-danger shadow-none",
        "attrs": "data-role='button' data-inline='true' data-mini='true'",
        "url": "{tp}{id}/{action}/",
        "icon": "delete fa-trash-o fa-lg",
    },
    "field_list": {
        "target": "inline_info",
        "class": "popup_inline btn {{btn_size}} btn-info shadow-none",
        "attrs": "data-role='button' data-inline='true' data-mini='true' "
        "data-inline-position='^tr, .tr:after' ",
        "attrs_in_menu": "data-inline-position='^tr, .tr:after'",
        "url": "{ap}table/{object_name}/{id}/{x1}/-/form/sublist/",
        "icon": "grid fa-caret-down fa-lg",
    },
    "field_list_get": {
        "target": "inline_info",
        "class": "popup_inline btn {{btn_size}} btn-info shadow-none",
        "attrs": "data-role='button' data-inline='true' data-mini='true'",
        "url": "{ap}{object_name}/{id}/{x1}/-/form/get/",
        "icon": "grid fa-caret-down fa-lg",
    },
    "field_action": {
        "target": "inline_edit",
        "class": "popup_inline btn {{btn_size}} btn-primary shadow-none",
        "attrs": "data-role='button' data-inline='true' data-mini='true' "
        "data-inline-position='^tr, .tr:after'",
        "attrs_in_menu": "data-inline-position='^tr, .tr:after'",
        "url": "{ap}{object_name}/{id}/{x1}/-/form/sublist/",
        "icon": "grid fa-angle-double-down fa-lg",
    },
    "field_edit": {
        "url": "{ap}table/{object_name}/{id}/{x1}/py/editor/",
        "icon": "edit fa-pencil-square-o fa-lg",
        "attrs": "data-inline-position='^tr, .tr:after'",
        "attrs_in_menu": "data-inline-position='^tr, .tr:after'",
    },
    "any_field_edit": {
        "url": "{app_path}table/{object_name}/{id}/{x1}/{x2}/editor/",
        "icon": "edit fa-pencil-square-o fa-lg",
    },
    "print": {
        "target": "_blank",
        "icon": "arrow-d fa-print fa-lg",
        "title": _("Print"),
    },
    "template_edit": {
        "icon": "client://mimetypes/x-office-presentation.png",
    },
    "pdf": {
        "target": "_blank",
        "url": "{tp}{id}/pdf/view/",
        "icon": "eye fa-eye fa-lg",
        "title": _("Convert to pdf"),
    },
    "odf": {
        "target": "_blank",
        "url": "{tp}{id}/odf/view/",
        "icon": "bullets fa-list fa-lg",
    },
    "xlsx": {
        "target": "_blank",
        "url": "{tp}{id}/xlsx/view/",
        "icon": "bullets fa-list fa-lg",
    },
    "null": {
        "target": "null",
        "url": "{tp}{id}/action/{action}/",
    },
    "inline": {
        "target": "inline_edit",
        "attrs": "data-inline-position='^tr, .tr:after'",
        "attrs_in_menu": "data-inline-position='^tr, .tr:after'",
    },
    "popup": {"target": "popup_edit"},
    "popup_edit": {"target": "popup_edit"},
    "popup_info": {"target": "popup_info"},
    "popup_delete": {"target": "popup_delete"},
    "refresh_frame": {"target": "refresh_frame"},
    "refresh_page": {"target": "refresh_page"},
    "_self": {"target": "_self"},
    "refresh_app": {"target": "refresh_app"},
    "back": {"target": "null"},
    "top": {"target": "_top"},
    "parent": {"target": "_parent"},
}


def unpack_value(standard_web_browser, value):
    """Unpack a value string, handling special formats.

    Supports pipe-delimited alternatives in brackets: ``[web_value|mobile_value]``.
    When ``standard_web_browser`` is True, the first alternative is returned;
    otherwise the second alternative (or first if only one exists).

    Args:
        standard_web_browser: Whether the client is a standard web browser.
        value: The string value to unpack.

    Returns:
        The unpacked string, or empty string if value is None or 'None'.
    """
    if not value:
        return ""
    if value == "None":
        return ""
    ret = value.strip()
    if ret.startswith("[") and ret.endswith("]"):
        x = ret[1:-1].split("|")
        if standard_web_browser:
            return x[0]
        else:
            return x[1] if len(x) > 1 else x[0]
    return ret


def get_action_parm(standard_web_browser, action, key, default_value=""):
    """Resolve an action parameter by searching through the action hierarchy.

    The action string may contain hyphen-separated components (e.g.
    'edit-new_row'). The lookup searches from right to left through
    these components in STANDARD_ACTIONS, falling back to the 'default'
    entry.

    Args:
        standard_web_browser: Whether the client is a standard web browser.
        action: The action identifier (may contain hyphens).
        key: The parameter key to look up (e.g. 'target', 'class').
        default_value: Value returned when no match is found.

    Returns:
        The unpacked parameter value, or default_value if not found.
    """
    ret = None
    for item in reversed(action.split("-")):
        if item in STANDARD_ACTIONS:
            if key in STANDARD_ACTIONS[item]:
                ret = STANDARD_ACTIONS[item][key]
                break
    if ret is None:
        ret = STANDARD_ACTIONS["default"].get(key, default_value)
    return unpack_value(standard_web_browser, ret)


def set_attrs(obj, params, attr_tab, standard_web_browser):
    """Set object attributes from a list of positional and named parameters.

    Parameters can be either positional (assigned in order to attr_tab
    entries) or named (``attr=value``). Named parameters are matched
    to attr_tab entries by name.

    Args:
        obj: The object whose attributes are being set.
        params: List of parameter strings.
        attr_tab: Ordered list of attribute names for positional matching.
        standard_web_browser: Whether the client is a standard web browser.
    """
    for i, pos in enumerate(params):
        matched = False
        for attr in attr_tab:
            if pos.replace(" ", "").startswith(attr + "="):
                setattr(
                    obj,
                    attr,
                    unpack_value(standard_web_browser, pos.split("=", 1)[1]),
                )
                matched = True
                break
        if not matched:
            if i < len(attr_tab):
                setattr(obj, attr_tab[i], unpack_value(standard_web_browser, pos))


def get_perm(app, table, action):
    """Build a Django permission string for the given action.

    Args:
        app: The Django app label.
        table: The model/table name (lowercase).
        action: The action identifier.

    Returns:
        A permission string like 'app.change_table' or 'app.delete_table',
        or an empty string if no specific permission applies.
    """
    if "edit" in action:
        return f"{app}.change_{table}"
    elif "delete" in action:
        return f"{app}.delete_{table}"
    else:
        return ""


class Action:
    """Represents a single UI action parsed from an action definition string.

    The action string format is::

        action,title,icon_name,target,attrs,tag_class,url

    with optional ``key=value`` pairs at the end. Action components separated
    by ``/`` provide x1/x2/x3 sub-parameters (e.g. ``edit/123/456``).
    """

    def __init__(self, actions_str, context, d):
        """Parse an action definition string and populate attributes.

        Args:
            actions_str: The comma-separated action definition string.
            context: The Django template context.
            d: A shared parameter dictionary that gets updated with
               action, x1, x2, x3 values.
        """
        self.d = d
        self.context = context
        self.action = ""
        self.title = ""
        self.icon_name = ""
        self.icon2 = ""
        self.target = ""
        self.attrs = ""
        self.attrs_in_menu = ""
        self.tag_class = ""
        self.tag_class_in_menu = ""
        self.url = ""

        self.x1 = ""
        self.x2 = ""
        self.x3 = ""

        standard_attr = (
            "action",
            "title",
            "icon_name",
            "target",
            "attrs",
            "tag_class",
            "url",
        )

        standard_web_browser = d.get("standard_web_browser", True)

        pos = actions_str.split(",")
        action = ""
        if "=" not in pos[0]:
            action = pos[0].strip()

        # Process trailing key=value pairs
        while True:
            if "=" in pos[-1]:
                if pos[-1].split("=")[0].strip() not in standard_attr:
                    break
                s = pos.pop().split("=", 1)
                if s[0] == "action":
                    action = s[1].strip()
                else:
                    setattr(self, s[0], unpack_value(standard_web_browser, s[1]))
            else:
                break

        if not action:
            return

        if "/" in action:
            x = action.split("/")
            self.x1 = escape(x[1].strip())
            if len(x) > 2:
                self.x2 = escape(x[2])
                if len(x) > 3:
                    self.x3 = escape(x[3].strip())
            action2 = x[0]
        else:
            action2 = action
        self.d["action"] = self.action = action2.split("-")[0]

        self.d["x1"] = self.x1
        self.d["x2"] = self.x2
        self.d["x3"] = self.x3

        set_attrs(self, pos[1:], standard_attr[1:], standard_web_browser)

        if "/" in action:
            tmp = action.split("/")
            self.name = tmp[0].split("-")[0] + "_" + tmp[1].replace("/", "_")
        else:
            self.name = action.split("-")[0]

        if not self.title:
            self.title = get_action_parm(
                standard_web_browser, action2, "title", action2
            )
            if not self.title:
                self.title = action2.split("-")[0]

        if not self.icon_name:
            self.icon_name = get_action_parm(standard_web_browser, action2, "icon")

        if not self.target:
            self.target = get_action_parm(
                standard_web_browser, action2, "target", "_blank"
            )

        btn_size = context.get("btn_size", settings.BOOTSTRAP_BUTTON_SIZE_CLASS)

        if not self.tag_class:
            self.tag_class = get_action_parm(
                standard_web_browser, action2, "class"
            ).replace("{{btn_size}}", btn_size)
        else:
            if self.tag_class.startswith("+"):
                self.tag_class = (
                    get_action_parm(standard_web_browser, action2, "class").replace(
                        "{{btn_size}}", btn_size
                    )
                    + " "
                    + self.tag_class[1:]
                )

        self.tag_class_in_menu = get_action_parm(
            standard_web_browser, action2, "class_in_menu"
        )

        if not self.attrs:
            self.attrs = get_action_parm(
                standard_web_browser, action2, "attrs"
            ).replace("{{btn_size}}", btn_size)
        else:
            if self.attrs.startswith("+"):
                self.attrs = (
                    get_action_parm(standard_web_browser, action2, "attrs").replace(
                        "{{btn_size}}", btn_size
                    )
                    + " "
                    + self.attrs[1:]
                )

        self.attrs_in_menu = get_action_parm(
            standard_web_browser, action2, "attrs_in_menu"
        )

        if not self.url or self.url.startswith("+"):
            url = get_action_parm(standard_web_browser, action2, "url")
            if self.url.startswith("+"):
                url += self.url[1:]
            self.url = url

        self.url = self.format(self.url)

        if self.icon_name:
            if not standard_web_browser:
                if "://" not in self.icon_name and "wx." not in self.icon_name:
                    if "fa-" in self.icon_name:
                        x = self.icon_name.split(" ")
                        for pos in x:
                            if "-" in pos and pos != "fa-lg":
                                if "fa-lg" in x:
                                    self.icon_name = "fa://%s?size=2" % pos
                                else:
                                    self.icon_name = "fa://%s?size=1" % pos
                    else:
                        self.icon_name = ""
            else:
                if "/" in self.icon_name:
                    x = self.icon_name.split("/")
                    self.icon_name = x[0]
                    self.icon2 = x[1]

    def format(self, s):
        """Format a URL template string, appending x1/x2/x3 query parameters.

        Args:
            s: The URL template string with ``{...}`` placeholders.

        Returns:
            The formatted URL string.
        """
        ret = s.format(**self.d).strip()
        if self.d["x1"]:
            buf = "x1=%s" % self.d["x1"]
            if self.d["x2"]:
                buf += "&x2=%s" % self.d["x2"]
                if self.d["x3"]:
                    buf += "&x3=%s" % self.d["x3"]
            if "?" in ret:
                ret += "&" + buf
            else:
                ret += "?" + buf
        return ret


def standard_dict(context, parm=None):
    """Build a standard parameter dictionary from a template context.

    Extracts commonly used values like path, base_path, app_path, table_path,
    and table_path_and_filter from the context. Additional parameters can
    be merged via the ``parm`` argument.

    Args:
        context: A Django template context (or dict-like with .flatten()).
        parm: Optional dict of extra parameters to merge.

    Returns:
        A dict with standard keys: path, bp, ap, tp, tpf, and any extras.
    """
    d = {}
    d.update(context.flatten())
    if parm:
        d.update(parm)

    if "request" in d:
        d["path"] = d["request"].path
    d["bp"] = d.get("base_path", "")
    if "app_path" in d:
        d["ap"] = d["app_path"]
    if "table_path" in d:
        d["tp"] = d["table_path"]
    if "table_path_and_filter" in d:
        d["tpf"] = d["table_path_and_filter"]

    return d


def actions_dict(context, actions_str):
    """Parse an actions string into a dictionary of Action objects.

    The actions string is a semicolon-separated list of action definitions.
    Items prefixed with ``|`` are placed in the secondary actions list.
    Permission checks (``?:edit``, ``app?:delete``) filter actions based
    on the current user's permissions.

    Args:
        context: The Django template context.
        actions_str: The semicolon-separated action definitions.

    Returns:
        A dictionary with keys: actions, actions2, action (first action),
        and all standard_dict keys.
    """
    d = standard_dict(context)

    if "object" in context:
        if hasattr(context["object"], "_meta"):
            d["table_name"] = context["object"]._meta.object_name
            d["id"] = context["object"].id
            d["object_name"] = context["object"]._meta.object_name
        else:
            d["table_name"] = "user_table"
            if context["object"] and "id" in context["object"]:
                d["id"] = context["object"]["id"]
            d["object_name"] = "object_name"

    d["child_tab"] = bool(context.get("rel_field"))

    actions = []
    actions2 = []
    test_actions2 = False
    act = actions
    for pos2 in actions_str.split(";"):
        pos = pos2.strip()
        if "?:" in pos:
            x = pos.split("?:", 1)
            if x[0]:
                perm = x[0]
            else:
                app = context["app_name"]
                table = context["table_name"].lower()
                perm = get_perm(app, table, x[1])

            if perm and not context["request"].user.has_perm(perm):
                continue
            pos = x[1]
        if not pos:
            continue
        if pos[0] == "|":
            act = actions2
            test_actions2 = True
        else:
            action = Action(pos, context, d)
            act.append(action)

    if (
        not test_actions2
        and len(actions) > 2
        and context.get("standard_web_browser", True)
    ):
        actions2 = actions[1:]
        actions = actions[:1]

    d["actions"] = actions
    d["actions2"] = actions2

    if len(actions) > 0:
        d["action"] = actions[0]
    elif len(actions2) > 0:
        d["action"] = actions2[0]
    else:
        d["action"] = []
    return d


def action_fun(
    context, action, title="", icon_name="", target="", attrs="", tag_class="", url=""
):
    """Convenience function to build a single action from explicit parameters.

    Constructs an action string, renders any Django template variables
    through the context, and returns the full actions dictionary.

    Args:
        context: The Django template context.
        action: The action identifier.
        title: Optional action title.
        icon_name: Optional icon name.
        target: Optional link target.
        attrs: Optional HTML attributes.
        tag_class: Optional CSS class.
        url: Optional URL pattern.

    Returns:
        An actions dictionary as returned by :func:`actions_dict`.
    """
    action_str = "%s,%s,%s,%s,%s,%s,%s" % (
        action,
        title,
        icon_name,
        target,
        attrs,
        tag_class,
        url,
    )
    t = Template(action_str)
    output2 = t.render(context)
    return actions_dict(context, output2)
