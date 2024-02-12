#! /usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY  ; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.

# Pytigon - wxpython and django application framework

# author: "Slawomir Cholaj (slawomir.cholaj@gmail.com)"
# copyright: "Copyright (C) ????/2013 Slawomir Cholaj"
# license: "LGPL 3.0"
# version: "0.1a"

from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.template import Template
from django.utils.html import escape

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
        "attrs": "data-role='button' data-inline='true' data-mini='true' data-inline-position='^tr, .tr:after'",
        "url": "{tp}{id}/{action}/",
        "icon": "edit fa-pencil fa-lg",
        #'icon': 'edit bi bi-pencil',
        #'icon': 'edit icon-whatsapp',
        #'icon': 'edit svg-categories--applications-office',
        "attrs_in_menu": "data-inline-position='^tr, .tr:after'",
    },
    #'edit2': {
    #    'target':  "popup_edit",
    #    'title': _('Update'),
    #    'class': "btn {{btn_size}} btn-outline-secondary edit",
    #    'attrs': "data-role='button' data-inline='true' data-mini='true' data-inline-position='^tr, .tr:after'",
    #    'url': "{tp}{id}/{action}/",
    #    'icon': 'edit fa-pencil fa-lg',
    #    'attrs_in_menu': "data-inline-position='^tr, .tr:after'",
    # },
    "delete": {
        "target": "popup_delete",
        "title": _("Delete"),
        "class": "popup_delete btn {{btn_size}} btn-danger shadow-none",
        "attrs": "data-role='button' data-inline='true' data-mini='true'",
        "url": "{tp}{id}/{action}/",
        "icon": "delete fa-trash-o fa-lg",
    },
    #'delete2': {
    #    'target': "popup_delete",
    #    'title': _('Delete'),
    #    'class': "popup_delete btn {{btn_size}} btn-outline-danger",
    #    'attrs': "data-role='button' data-inline='true' data-mini='true'",
    #    'url': "{tp}{id}/{action}/",
    #    'icon': 'delete fa-trash-o fa-lg'
    # },
    "field_list": {
        "target": "inline_info",
        "class": "popup_inline btn {{btn_size}} btn-info shadow-none",
        "attrs": "data-role='button' data-inline='true' data-mini='true' data-inline-position='^tr, .tr:after' ",
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
    # field_action do usunięcia
    "field_action": {
        "target": "inline_edit",
        "class": "popup_inline btn {{btn_size}} btn-primary shadow-none",
        "attrs": "data-role='button' data-inline='true' data-mini='true' data-inline-position='^tr, .tr:after'",
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
    if value:
        if value == "None":
            return ""
        ret = value.strip()
        if ret.startswith("[") and ret.endswith("]"):
            x = ret[1:-1].split("|")
            if standard_web_browser:
                return x[0]
            else:
                if len(x) > 1:
                    return x[1]
                else:
                    return x[0]
        return ret
    return ""


def get_action_parm(standard_web_browser, action, key, default_value=""):
    global STANDARD_ACTIONS
    ret = None
    p = action.split("-")
    for item in reversed(p):
        if item in STANDARD_ACTIONS:
            if key in STANDARD_ACTIONS[item]:
                ret = STANDARD_ACTIONS[item][key]
                break
    if ret == None:
        if key in STANDARD_ACTIONS["default"]:
            ret = STANDARD_ACTIONS["default"][key]
    return unpack_value(standard_web_browser, ret)


def set_attrs(obj, params, attr_tab, standard_web_browser):
    i = 0
    for pos in params:
        equal_sign = False
        for attr in attr_tab:
            if pos.replace(" ", "").startswith(attr + "="):
                setattr(
                    obj, attr, unpack_value(standard_web_browser, pos.split("=", 1)[1])
                )
                equal_sign = True
                break
        if not equal_sign:
            if len(attr_tab) > i:
                setattr(obj, attr_tab[i], unpack_value(standard_web_browser, pos))
        i += 1


def get_perm(app, table, action):
    if "edit" in action:
        return "%s.change_%s" % (app, table)
    elif "delete" in action:
        return "%s.delete_%s" % (app, table)
    else:
        return ""


class Action:
    def __init__(self, actions_str, context, d):
        # actions_str: action,title,icon_name,target,attrs,tag_class,url
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

        if "standard_web_browser" in d:
            standard_web_browser = d["standard_web_browser"]
        else:
            standard_web_browser = 1

        pos = actions_str.split(",")
        action = ""
        if "=" not in pos[0]:
            action = pos[0].strip()

        while True:
            if "=" in pos[-1]:
                if pos[-1].split("=")[0].strip() not in standard_attr:
                    break
                s = pos.pop().split("=", 1)
                if s[0] == "action":
                    action = s.strip()
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
        # if len(pos)>1:
        #    self.title = unpack_value(standard_web_browser, pos[1])
        #    if len(pos)>2:
        #        self.icon = unpack_value(standard_web_browser, pos[2])
        #        if len(pos)>3:
        #            self.target = unpack_value(standard_web_browser, pos[3])
        #            if len(pos)>4:
        #                self.attrs = unpack_value(standard_web_browser, pos[4])
        #                if len(pos)>5:
        #                    self.tag_class = unpack_value(standard_web_browser, pos[5])
        #                    if len(pos)>6:
        #                        self.url = unpack_value(standard_web_browser, pos[6])

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

        if "btn_size" in context:
            btn_size = context["btn_size"]
        else:
            btn_size = settings.BOOTSTRAP_BUTTON_SIZE_CLASS

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
                if not "://" in self.icon_name and not "wx." in self.icon_name:
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
    d = {}
    d.update(context.flatten())
    if parm:
        d.update(parm)

    d["path"] = d["request"].path
    d["bp"] = d["base_path"]
    if "app_path" in d:
        d["ap"] = d["app_path"]
    if "table_path" in d:
        d["tp"] = d["table_path"]
    if "table_path_and_filter" in d:
        d["tpf"] = d["table_path_and_filter"]

    return d


def actions_dict(context, actions_str):
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

    if "rel_field" in context and context["rel_field"]:
        d["child_tab"] = True
    else:
        d["child_tab"] = False

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
                print("perm: ", context["request"].user, perm)
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

    if not test_actions2 and len(actions) > 2 and context["standard_web_browser"]:
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


# actions_str: action,title,icon_name,target,attrs,tag_class,url
def action_fun(
    context, action, title="", icon_name="", target="", attrs="", tag_class="", url=""
):
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
    d = actions_dict(context, output2)
    # return standard_dict(context, d)
    return d
