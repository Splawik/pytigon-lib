import os
import codecs
from django.conf import settings
from django.template import Origin, TemplateDoesNotExist
from django.utils._os import safe_join
from django.template.loaders.base import Loader as BaseLoader
import django.template.loaders.filesystem
from django.core.exceptions import SuspiciousFileOperation
from pytigon_lib.schdjangoext.django_ihtml import ihtml_to_html

CONTENT_TYPE = None


def compile_template(
    template_name, template_dirs=None, tried=None, compiled=None, force=False
):
    """Compile ihtml templates to html based on language settings."""

    def get_template_sources(template_name, template_dirs=None):
        """Generate paths for template sources."""
        if not template_dirs:
            template_dirs = settings.TEMPLATES[0]["DIRS"]
        for template_dir in template_dirs:
            try:
                yield safe_join(
                    template_dir + "_src", template_name.replace(".html", ".ihtml")
                )
            except (UnicodeDecodeError, ValueError):
                continue

    if not template_dirs:
        template_dirs = settings.TEMPLATES[0]["DIRS"]

    template_name_base = template_name
    for lang_code, _ in settings.LANGUAGES:
        template_name_base = template_name_base.replace(f"_{lang_code}.html", ".html")

    for filepath in get_template_sources(template_name_base, template_dirs):
        filepath2 = filepath.replace("_src", "").replace(".ihtml", ".html")
        if "site-packages" in filepath2:
            filepath2 = filepath2.replace(settings.PRJ_PATH, settings.PRJ_PATH_ALT)

        try:
            if not os.path.exists(filepath):
                continue

            if not os.path.exists(os.path.dirname(filepath2)):
                os.makedirs(os.path.dirname(filepath2))

            write = (
                force
                or not os.path.exists(filepath2)
                or os.path.getmtime(filepath) > os.path.getmtime(filepath2)
            )

            if write:
                for lang_code, _ in settings.LANGUAGES:
                    try:
                        ret = ihtml_to_html(filepath, lang=lang_code)
                        if ret:
                            output_path = (
                                filepath2
                                if lang_code == "en"
                                else filepath2.replace(".html", f"_{lang_code}.html")
                            )
                            with codecs.open(output_path, "w", encoding="utf-8") as f:
                                f.write(ret)
                            if compiled is not None:
                                compiled.append(output_path)
                    except Exception:
                        continue

            if tried is not None:
                tried.append(filepath)
        except IOError:
            if tried is not None:
                tried.append(filepath)


class FSLoader(django.template.loaders.filesystem.Loader):
    """File system loader for templates."""

    is_usable = True

    def get_template_sources(self, template_name):
        """Generate template sources from directories."""
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
        """Read template contents."""
        try:
            with open(origin.name, encoding=self.engine.file_charset) as fp:
                return fp.read()
        except FileNotFoundError:
            if "_" in origin.name:
                base_name = origin.name.rsplit("_", 1)[0] + ".html"
                try:
                    with open(base_name, encoding=self.engine.file_charset) as fp:
                        return fp.read()
                except FileNotFoundError:
                    raise TemplateDoesNotExist(origin)
            raise TemplateDoesNotExist(origin)


class Loader(BaseLoader):
    """Loader to compile ihtml files to html and load based on language."""

    is_usable = True

    def get_template_sources(self, template_name, template_dirs=None):
        """Generate paths for template sources."""
        if not template_dirs:
            template_dirs = settings.TEMPLATES[0]["DIRS"]
        for template_dir in template_dirs:
            try:
                for lang_code, _ in settings.LANGUAGES:
                    if f"_{lang_code}.html" in template_name:
                        template_name = template_name.replace(
                            f"_{lang_code}.html", ".html"
                        )
                yield safe_join(
                    template_dir + "_src", template_name.replace(".html", ".ihtml")
                )
            except (UnicodeDecodeError, ValueError):
                continue

    def get_contents(self, origin):
        """Read and compile template contents."""
        filepath = origin
        filepath2 = filepath.replace("_src", "").replace(".ihtml", ".html")
        try:
            if os.path.exists(filepath):
                if not os.path.exists(os.path.dirname(filepath2)):
                    os.makedirs(os.path.dirname(filepath2))

                write = not os.path.exists(filepath2) or os.path.getmtime(
                    filepath
                ) > os.path.getmtime(filepath2)

                if write:
                    for lang_code, _ in settings.LANGUAGES:
                        try:
                            ret = ihtml_to_html(filepath, lang=lang_code)
                            if ret:
                                output_path = (
                                    filepath2
                                    if lang_code == "en"
                                    else filepath2.replace(
                                        ".html", f"_{lang_code}.html"
                                    )
                                )
                                with codecs.open(
                                    output_path, "w", encoding="utf-8"
                                ) as f:
                                    f.write(ret)
                        except Exception:
                            continue
        except Exception:
            pass
        raise TemplateDoesNotExist(origin)


class DBLoader(BaseLoader):
    """Loader to compile ihtml files from database to html."""

    is_usable = True

    def get_template_sources(self, template_name, template_dirs=None):
        """Generate paths for template sources from database."""
        if not template_dirs:
            template_dirs = settings.TEMPLATES[0]["DIRS"]

        for template_dir in [settings.DATA_PATH + "/plugins"]:
            try:
                if template_name.startswith("db/"):
                    for lang_code, _ in settings.LANGUAGES:
                        if f"_{lang_code}.html" in template_name:
                            template_name = template_name.replace(
                                f"_{lang_code}.html", ".html"
                            )
                    yield safe_join(
                        template_dir + "_src", template_name.replace(".html", ".ihtml")
                    )
            except (UnicodeDecodeError, ValueError):
                continue

    def get_contents(self, origin):
        """Read and compile template contents from database."""
        global CONTENT_TYPE
        filepath = origin
        filepath2 = filepath.replace("_src", "").replace(".ihtml", ".html")
        if "/db/" in filepath:
            if not CONTENT_TYPE:
                from django.contrib.contenttypes.models import ContentType

                CONTENT_TYPE = ContentType

            try:
                parts = filepath.split("/")
                app = parts[-2] if parts[-2] != "db" else None
                model_name = parts[-1].split(".")[0].split("-")[0]
                obj_id = int(parts[-1].split("-")[1])
                field_name = parts[-1].split("-")[2]

                model = CONTENT_TYPE.objects.get(
                    app_label=app, model=model_name.lower()
                ).model_class()
                obj = model.objects.filter(pk=obj_id).first()

                if obj:
                    if not os.path.exists(os.path.dirname(filepath2)):
                        os.makedirs(os.path.dirname(filepath2))

                    write = not os.path.exists(
                        filepath2
                    ) or obj.update_time.timestamp() > os.path.getmtime(filepath2)

                    if write:
                        for lang_code, _ in settings.LANGUAGES:
                            try:
                                ret = ihtml_to_html(
                                    None,
                                    input_str=getattr(obj, field_name),
                                    lang=lang_code,
                                )
                                if ret:
                                    output_path = (
                                        filepath2
                                        if lang_code == "en"
                                        else filepath2.replace(
                                            ".html", f"_{lang_code}.html"
                                        )
                                    )
                                    with codecs.open(
                                        output_path, "w", encoding="utf-8"
                                    ) as f:
                                        f.write(ret)
                            except Exception:
                                continue
            except Exception:
                pass
        raise TemplateDoesNotExist(origin)
