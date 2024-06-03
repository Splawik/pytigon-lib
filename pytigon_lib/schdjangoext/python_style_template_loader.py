#!/usr/bin/python
# -*- coding: utf-8 -*-
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation; either version 3, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTIBILITY
# or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details

# Pytigon - wxpython and django application framework

# author: "Slawomir Cholaj (slawomir.cholaj@gmail.com)"
# copyright: "Copyright (C) ????/2012 Slawomir Cholaj"
# license: "LGPL 3.0"
# version: "0.1a"

import os
import codecs

from django.conf import settings
from django.template import Origin, TemplateDoesNotExist
from django.utils._os import safe_join
from django.template.loaders.base import Loader as BaseLoader
import django.template.loaders.filesystem
import django.template.loaders.app_directories
from django.core.exceptions import SuspiciousFileOperation

from pytigon_lib.schdjangoext.django_ihtml import ihtml_to_html

CONTENT_TYPE = None


def compile_template(
    template_name, template_dirs=None, tried=None, compiled=None, force=False
):
    def get_template_sources(template_name, template_dirs=None):
        if not template_dirs:
            template_dirs = settings.TEMPLATES[0]["DIRS"]
        for template_dir in template_dirs:
            try:
                yield safe_join(
                    template_dir + "_src", template_name.replace(".html", ".ihtml")
                )
            except UnicodeDecodeError:
                raise
            except ValueError:
                pass

    if not template_dirs:
        template_dirs = settings.TEMPLATES[0]["DIRS"]

    template_name_base = template_name
    for pos in settings.LANGUAGES:
        template_name_base = template_name_base.replace("_" + pos[0] + ".html", ".html")
        for filepath in get_template_sources(template_name_base, template_dirs):
            # if not type(filepath) == str:
            #    continue
            filepath2 = filepath.replace("_src", "").replace(".ihtml", ".html")
            try:
                write = False
                if os.path.exists(filepath):
                    if not os.path.exists(os.path.dirname(filepath2)):
                        os.makedirs(os.path.dirname(filepath2))
                    if os.path.exists(filepath2):
                        if force:
                            write = True
                        else:
                            time2 = os.path.getmtime(filepath2)
                            time1 = os.path.getmtime(filepath)
                            if time1 > time2:
                                write = True
                    else:
                        write = True
                    if write:
                        langs = []
                        for pos in settings.LANGUAGES:
                            langs.append(pos[0])
                        for lang in langs:
                            try:
                                ret = ihtml_to_html(filepath, lang=lang)
                                if ret:
                                    try:
                                        if lang == "en":
                                            with codecs.open(
                                                filepath2, "w", encoding="utf-8"
                                            ) as f:
                                                f.write(ret)
                                            if compiled != None:
                                                compiled.append(filepath2)
                                        else:
                                            with codecs.open(
                                                filepath2.replace(
                                                    ".html", "_" + lang + ".html"
                                                ),
                                                "w",
                                                encoding="utf-8",
                                            ) as f:
                                                f.write(ret)
                                            if compiled != None:
                                                compiled.append(
                                                    filepath2.replace(
                                                        ".html", "_" + lang + ".html"
                                                    )
                                                )
                                    except:
                                        import traceback
                                        import sys

                                        print(sys.exc_info())
                                        print(traceback.print_exc())
                            except:
                                pass
                    if tried != None:
                        tried.append(filepath)
            except IOError:
                if tried != None:
                    tried.append(filepath)


class FSLoader(django.template.loaders.filesystem.Loader):
    is_usable = True

    def get_template_sources(self, template_name):
        for template_dir in self.get_dirs():
            try:
                name = safe_join(template_dir, template_name)
            except SuspiciousFileOperation:
                continue

            yield Origin(
                name=name,
                template_name=template_name,
                loader=self,
            )

            if "_" in name:
                x = name.rsplit("_", 1)
                if len(x[1]) == 7 and x[1].endswith(".html"):
                    yield Origin(
                        name=x[0] + ".html",
                        template_name=template_name,
                        loader=self,
                    )

    def get_contents(self, origin):
        try:
            with open(origin.name, encoding=self.engine.file_charset) as fp:
                return fp.read()
        except FileNotFoundError:
            if "_" in origin.name:
                x = origin.name.rsplit("_", 1)
                if len(x[1]) == 7 and x[1].endswith(".html"):
                    try:
                        with open(
                            x[0] + ".html", encoding=self.engine.file_charset
                        ) as fp:
                            return fp.read()
                    except FileNotFoundError:
                        raise TemplateDoesNotExist(origin)
            raise TemplateDoesNotExist(origin)


class Loader(BaseLoader):
    """Loader compile ihtml file to standard html file and based on language load related compiled template"""

    is_usable = True

    def get_template_sources(self, template_name, template_dirs=None):
        if not template_dirs:
            template_dirs = settings.TEMPLATES[0]["DIRS"]
        for template_dir in template_dirs:
            try:
                for pos in settings.LANGUAGES:
                    if "_" + pos[0] + ".html" in template_name:
                        template_name = template_name.replace(
                            "_" + pos[0] + ".html", ".html"
                        )

                yield safe_join(
                    template_dir + "_src", template_name.replace(".html", ".ihtml")
                )
            except UnicodeDecodeError:
                raise
            except ValueError:
                pass

    def get_contents(self, origin):
        filepath = origin
        filepath2 = filepath.replace("_src", "").replace(".ihtml", ".html")
        try:
            write = False
            if os.path.exists(filepath):
                if not os.path.exists(os.path.dirname(filepath2)):
                    os.makedirs(os.path.dirname(filepath2))
                if os.path.exists(filepath2):
                    time2 = os.path.getmtime(filepath2)
                    time1 = os.path.getmtime(filepath)
                    if time1 > time2:
                        write = True
                else:
                    write = True
                if write:
                    langs = []
                    for pos in settings.LANGUAGES:
                        langs.append(pos[0])
                    for lang in langs:
                        try:
                            ret = ihtml_to_html(filepath, lang=lang)
                            if ret:
                                try:
                                    if lang == "en":
                                        with codecs.open(
                                            filepath2, "w", encoding="utf-8"
                                        ) as f:
                                            f.write(ret)
                                    else:
                                        with codecs.open(
                                            filepath2.replace(
                                                ".html", "_" + lang + ".html"
                                            ),
                                            "w",
                                            encoding="utf-8",
                                        ) as f:
                                            f.write(ret)
                                except:
                                    try:
                                        if lang == "en":
                                            with codecs.open(
                                                filepath2, "r", encoding="utf-8"
                                            ) as f:
                                                if f.read() != ret:
                                                    import traceback
                                                    import sys

                                                    print(sys.exc_info())
                                                    print(traceback.print_exc())
                                        else:
                                            with codecs.open(
                                                filepath2.replace(
                                                    ".html", "_" + lang + ".html"
                                                ),
                                                "r",
                                                encoding="utf-8",
                                            ) as f:
                                                if f.read() != ret:
                                                    import traceback
                                                    import sys

                                                    print(sys.exc_info())
                                                    print(traceback.print_exc())
                                    except:
                                        import traceback
                                        import sys

                                        print(sys.exc_info())
                                        print(traceback.print_exc())
                        except:
                            pass
        except:
            pass
        raise TemplateDoesNotExist(origin)


class DBLoader(BaseLoader):
    """Loader compile ihtml file to standard html file and based on language load related compiled template"""

    is_usable = True

    def get_template_sources(self, template_name, template_dirs=None):
        if not template_dirs:
            template_dirs = settings.TEMPLATES[0]["DIRS"]

        for template_dir in [
            settings.DATA_PATH + "/plugins",
        ]:
            try:
                if template_name.startswith("db/"):
                    for pos in settings.LANGUAGES:
                        if "_" + pos[0] + ".html" in template_name:
                            template_name = template_name.replace(
                                "_" + pos[0] + ".html", ".html"
                            )
                    yield safe_join(
                        template_dir + "_src", template_name.replace(".html", ".ihtml")
                    )
            except UnicodeDecodeError:
                raise
            except ValueError:
                pass

    def get_contents(self, origin):
        global CONTENT_TYPE
        filepath = origin
        filepath2 = filepath.replace("_src", "").replace(".ihtml", ".html")
        if "/db/" in filepath:
            if not CONTENT_TYPE:
                from django.contrib.contenttypes.models import ContentType

                CONTENT_TYPE = ContentType
            try:
                write = False

                x = filepath.split("/")
                if x[-2] == "db":
                    app = None
                    xx = x[-1].split(".")[0]
                else:
                    app = x[-2]
                    xx = x[-1].split(".")[0]
                parts = xx.split("-")
                if app:
                    model = CONTENT_TYPE.objects.get(
                        app_label=app, model=parts[0].lower()
                    ).model_class()
                else:
                    model = CONTENT_TYPE.objects.get(
                        model=parts[0].lower()
                    ).model_class()
                id = int(parts[1])
                field_name = parts[2]
                obj = model.objects.filter(pk=id).first()

                if obj:
                    if not os.path.exists(os.path.dirname(filepath2)):
                        os.makedirs(os.path.dirname(filepath2))
                    if os.path.exists(filepath2):
                        time2 = os.path.getmtime(filepath2)
                        time1 = obj.update_time.timestamp()
                        if time1 > time2:
                            write = True
                    else:
                        write = True
                    if write:
                        langs = []
                        for pos in settings.LANGUAGES:
                            langs.append(pos[0])
                        for lang in langs:
                            try:
                                ret = ihtml_to_html(
                                    None, input_str=getattr(obj, field_name), lang=lang
                                )
                                if ret:
                                    try:
                                        if lang == "en":
                                            with codecs.open(
                                                filepath2, "w", encoding="utf-8"
                                            ) as f:
                                                f.write(ret)
                                        else:
                                            with codecs.open(
                                                filepath2.replace(
                                                    ".html", "_" + lang + ".html"
                                                ),
                                                "w",
                                                encoding="utf-8",
                                            ) as f:
                                                f.write(ret)
                                    except:
                                        try:
                                            if lang == "en":
                                                with codecs.open(
                                                    filepath2, "r", encoding="utf-8"
                                                ) as f:
                                                    if f.read() != ret:
                                                        import traceback
                                                        import sys

                                                        print(sys.exc_info())
                                                        print(traceback.print_exc())
                                            else:
                                                with codecs.open(
                                                    filepath2.replace(
                                                        ".html", "_" + lang + ".html"
                                                    ),
                                                    "r",
                                                    encoding="utf-8",
                                                ) as f:
                                                    if f.read() != ret:
                                                        import traceback
                                                        import sys

                                                        print(sys.exc_info())
                                                        print(traceback.print_exc())
                                        except:
                                            import traceback
                                            import sys

                                            print(sys.exc_info())
                                            print(traceback.print_exc())
                            except:
                                pass
            except:
                pass
        raise TemplateDoesNotExist(origin)
