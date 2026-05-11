"""
Indented markdown processor for wiki-style content.

Converts indented wiki markup with embedded object renderers to HTML.
Supports custom object renderers that can be registered to handle
special syntax blocks (marked with % prefix).

Key components:
- BaseObjRenderer: Base class for custom object renderers
- IndentMarkdownProcessor: Main conversion engine
- Registration system for custom renderers
"""

import json
import logging
from typing import Any, Dict, List, Optional

import markdown
from django.template.loader import select_template

logger = logging.getLogger(__name__)

# Global registry of named object renderers
REG_OBJ_RENDERER: Dict[str, type] = {}


class BaseObjRenderer:
    """Base class for wiki object renderers.

    Subclass this to create custom renderers for special wiki syntax
    blocks. Override get_info(), gen_context(), and get_renderer_template_name()
    to customize behavior.

    Attributes:
        extra_info: Additional data associated with the renderer instance.
        line_number: Current line number in the source document.
    """

    def __init__(self, extra_info: str = "") -> None:
        """Initialize the renderer.

        Args:
            extra_info: Additional information passed from the wiki source.
        """
        self.extra_info = extra_info
        self.line_number = 0

    def _get_line_number(self, parent_processor: Any) -> int:
        """Calculate the absolute line number by walking up processor hierarchy.

        Args:
            parent_processor: The parent IndentMarkdownProcessor instance.

        Returns:
            Absolute line number, or -1 if line tracking is disabled.
        """
        if self.line_number == 0:
            parent = parent_processor
            if parent.line_number < 0:
                return -1

            while parent is not None:
                self.line_number += parent.line_number
                parent = getattr(parent, "parent_processor", None)

        return self.line_number

    @staticmethod
    def get_info() -> Dict[str, Any]:
        """Return metadata about this renderer.

        Returns:
            Dictionary with keys: name, title, icon, show_form, inline_content.
        """
        return {
            "name": "",
            "title": "",
            "icon": "",
            "show_form": False,
            "inline_content": False,
        }

    def get_edit_form(self):
        """Return the edit form class for this renderer, or None."""
        return None

    def convert_form_to_dict(self, form, old_dict=None) -> Dict:
        """Convert form data to a dictionary.

        Args:
            form: Django form instance.
            old_dict: Previous dictionary values (unused by default).

        Returns:
            Dictionary from form.cleaned_data.
        """
        return form.cleaned_data

    def form_from_dict(self, form_class, param: Optional[Dict] = None):
        """Create a form instance from a dictionary of initial values.

        Args:
            form_class: Django form class to instantiate.
            param: Optional dictionary of initial values.

        Returns:
            Form instance.
        """
        if param:
            return form_class(initial=param)
        return form_class()

    def gen_context(self, param: Any, lines: List[str], output_format: str, parent_processor: Any) -> Dict[str, Any]:
        """Generate template context for rendering.

        Args:
            param: Parameters from the wiki source.
            lines: Content lines belonging to this block.
            output_format: Target output format (e.g., 'html').
            parent_processor: Parent IndentMarkdownProcessor.

        Returns:
            Template context dictionary.
        """
        return {}

    def get_renderer_template_name(self) -> Optional[str]:
        """Return the Django template name for rendering, or None."""
        return None

    def get_edit_template_name(self) -> str:
        """Return the Django template name for the edit form."""
        return "schwiki/wikiobj_edit.html"

    def edit_on_page_link(self, parent_processor: Any, right: bool = False) -> str:
        """Generate an edit link for inline editing on the wiki page.

        Args:
            parent_processor: Parent IndentMarkdownProcessor.
            right: If True, position the link on the right side.

        Returns:
            Django template snippet for the edit link.
        """
        line_number = self._get_line_number(parent_processor)
        title = self.get_info()["title"]

        if line_number < 0:
            return ""

        buf = " wiki-object-edit-right" if right else ""
        href = (
            f"{{{{base_path}}}}schwiki/edit_object_on_page/"
            f"{{{{object.id}}}}/{line_number}/?name={{{{name}}}}"
            f"&only_content=1"
        )
        return f"""
            {{% if perms.wiki.add_page %}}
                <a class="wiki-object-edit{buf}" href="{href}" target="popup_edit" title="{title} properties">
                    {title} <span class="fa fa-cog fa-2" />
                </a>
            {{% endif %}}
        """

    def render(self, param: Any, lines: List[str], output_format: str, parent_processor: Any) -> str:
        """Render this object to HTML using its template.

        Args:
            param: Parameters from the wiki source.
            lines: Content lines belonging to this block.
            output_format: Target output format.
            parent_processor: Parent IndentMarkdownProcessor.

        Returns:
            Rendered HTML string.
        """
        template_name = self.get_renderer_template_name()
        context = self.gen_context(param, lines, output_format, parent_processor)
        context["output_format"] = output_format
        context["line_number"] = self._get_line_number(parent_processor)

        if template_name:
            t = select_template([template_name])
            ret = t.render(context)
            # Restore Django template tags that were escaped
            return ret.replace("[%", "{%").replace("%]", "%}").replace("[{", "{{").replace("}]", "}}")
        return context.get("content", f"[[[{self.extra_info}]]]")


def register_obj_renderer(obj_name: str, obj_renderer: type) -> None:
    """Register a custom object renderer class.

    Args:
        obj_name: Name used in wiki source to reference this renderer.
        obj_renderer: Renderer class (subclass of BaseObjRenderer).
    """
    if obj_name not in REG_OBJ_RENDERER:
        REG_OBJ_RENDERER[obj_name] = obj_renderer


def get_obj_renderer(obj_name: str) -> BaseObjRenderer:
    """Get a renderer instance for the given object name.

    Falls back to BaseObjRenderer if no specific renderer is registered,
    passing the object name as extra_info.

    Args:
        obj_name: Name of the object renderer to retrieve.

    Returns:
        An instance of the appropriate renderer.
    """
    renderer_class = REG_OBJ_RENDERER.get(obj_name, BaseObjRenderer)
    return renderer_class(obj_name)


def get_indent(s: str) -> int:
    """Count leading whitespace characters in a string.

    Args:
        s: Input string.

    Returns:
        Number of leading whitespace characters.
    """
    return len(s) - len(s.lstrip())


def unindent(lines: List[str]) -> List[str]:
    """Remove common leading whitespace from a list of lines.

    Args:
        lines: List of text lines, possibly with leading whitespace.

    Returns:
        Lines with common leading whitespace removed.
    """
    indent = next((get_indent(line) for line in lines if line), -1)
    if indent > 0:
        return [line[indent:] for line in lines]
    return lines


def markdown_to_html(buf: str) -> str:
    """Convert markdown text to HTML using configured extensions.

    Args:
        buf: Markdown source text.

    Returns:
        HTML string.

    Raises:
        Exception: If markdown conversion fails.
    """
    try:
        return markdown.markdown(
            buf,
            extensions=[
                "abbr",
                "attr_list",
                "def_list",
                "fenced_code",
                "footnotes",
                "md_in_html",
                "tables",
                "admonition",
                "codehilite",
            ],
        )
    except Exception:
        logger.exception("Markdown conversion failed")
        raise


class IndentMarkdownProcessor:
    """Process indented wiki markup into rendered HTML.

    Handles embedded object renderers (marked with % prefix), named
    references, and standard markdown formatting.

    Attributes:
        output_format: Target output format (e.g., 'html').
        parent_processor: Parent processor for nested rendering.
        named_renderers: Dictionary of named renderer references.
        uri: Optional URI context for rendering.
    """

    def __init__(
        self,
        output_format: str = "html",
        parent_processor: Optional["IndentMarkdownProcessor"] = None,
        uri: Optional[str] = None,
        line_number: int = 0,
    ) -> None:
        """Initialize the processor.

        Args:
            output_format: Target output format.
            parent_processor: Parent processor for hierarchy.
            uri: Optional URI for context.
            line_number: Starting line number.
        """
        self.output_format = output_format
        self.parent_processor = parent_processor
        self.named_renderers: Dict[str, str] = {}
        self.uri = uri
        self.lines: Optional[List[str]] = None
        self.line_number = line_number

    def get_root(self) -> "IndentMarkdownProcessor":
        """Get the root processor in the hierarchy.

        Returns:
            The topmost IndentMarkdownProcessor.
        """
        if self.parent_processor:
            return self.parent_processor.get_root()
        return self

    @staticmethod
    def _json_dumps(obj: Any) -> str:
        """Serialize to JSON, escaping newlines.

        Args:
            obj: Object to serialize.

        Returns:
            JSON string with escaped newlines.
        """
        return json.dumps(obj).replace("\n", "\\n")

    @staticmethod
    def _json_loads(s: str) -> Any:
        """Deserialize JSON, restoring escaped newlines.

        Args:
            s: JSON string with escaped newlines.

        Returns:
            Parsed object, or the original string if not JSON.
        """
        if s and s[0] == "{":
            return json.loads(s.replace("\\n", "\n"))
        return s

    def _render_obj(self, config: str, lines: Optional[List[str]]) -> str:
        """Render an embedded object from its configuration string.

        Args:
            config: Configuration string starting with %.
            lines: Content lines belonging to this object.

        Returns:
            Rendered HTML string.
        """
        parts = config.split("#", 1)
        param = self._json_loads(parts[1].strip()) if len(parts) > 1 else None
        obj_name = parts[0].strip()[1:].strip().rstrip(":")

        # Handle named references
        if "name/" in obj_name:
            if lines:
                name = obj_name.split("name/")[1].strip()
                self.named_renderers[name] = lines[0].strip()
            return ""

        # Resolve named renderer references
        if obj_name in self.named_renderers:
            saved_line_number = self.line_number
            self.line_number = -1
            ret = self._render_obj(self.named_renderers[obj_name], lines)
            self.line_number = saved_line_number
            return ret

        return self.render_obj(obj_name, param, lines)

    def render_obj(self, obj_name: str, param: Any, lines: Optional[List[str]] = None) -> str:
        """Render a named object using its registered renderer.

        Args:
            obj_name: Name of the renderer to use.
            param: Parameters for the renderer.
            lines: Content lines for the renderer.

        Returns:
            Rendered HTML string.
        """
        renderer = get_obj_renderer(obj_name)
        return renderer.render(param, lines, self.output_format, self)

    def render_wiki(self, wiki_source: str) -> str:
        """Convert wiki markdown source to HTML.

        Args:
            wiki_source: Raw wiki source text.

        Returns:
            HTML string.
        """
        return markdown_to_html(wiki_source)

    def convert(self, indent_wiki_source: str) -> str:
        """Convert indented wiki source to HTML.

        Parses the source line by line, identifying object renderer blocks
        (marked with %), rendering them, and processing the remaining
        content as markdown.

        Args:
            indent_wiki_source: Full wiki source text with indentation.

        Returns:
            Rendered HTML string.
        """
        registrations: List[List] = []  # [config, rendered_result]
        line_buffer: List[str] = []
        func_buffer: List[str] = []
        in_func = False
        in_func_indent = 0
        root = self.get_root()
        self.lines = indent_wiki_source.replace("\r", "").split("\n")

        sentinel = "."

        for line in self.lines + [sentinel]:
            self.line_number += 1
            stripped = line.strip()

            if in_func:
                if line:
                    indent = get_indent(line)
                    if indent > in_func_indent:
                        func_buffer.append(line[in_func_indent:])
                    else:
                        # End of function block - render it
                        in_func = False
                        saved_line = self.line_number
                        self.line_number -= len(func_buffer) + 1
                        registrations[-1].append(self._render_obj(registrations[-1][0], unindent(func_buffer)))
                        self.line_number = saved_line
                        func_buffer = []
                else:
                    func_buffer.append("")

            if not in_func:
                if stripped.startswith("%"):
                    config = stripped[1:]
                    # Check if this opens a block (ends with ':')
                    last_char = config.split("#")[0].strip()[-1] if "#" in config else config.strip()[-1]

                    if last_char == ":":
                        in_func = True
                        in_func_indent = get_indent(line)
                        line_buffer.append(f"[[[{len(registrations)}]]]")
                        registrations.append([stripped])
                    else:
                        # Inline object - render immediately
                        line_buffer.append(f"[[[{len(registrations)}]]]")
                        registrations.append([stripped, self._render_obj(stripped, None)])
                else:
                    if stripped != sentinel:
                        line_buffer.append(line)

        # Flush any remaining function block
        if in_func:
            saved_line = self.line_number
            self.line_number -= len(func_buffer) + 1
            registrations[-1].append(self._render_obj(registrations[-1][0], unindent(func_buffer)))
            self.line_number = saved_line

        # Build output with rendered objects
        buf_out = "\n".join(line_buffer)
        buf_out = self.render_wiki(buf_out)

        for i, reg_entry in enumerate(registrations):
            placeholder = f"[[[{i}]]]"
            if placeholder in buf_out:
                buf_out = buf_out.replace(placeholder, reg_entry[1])

        return buf_out


def imd2html(buf: str) -> str:
    """Convenience function: convert indented markdown to HTML.

    Args:
        buf: Indented wiki/markdown source.

    Returns:
        Rendered HTML string.
    """
    return IndentMarkdownProcessor(output_format="html").convert(buf)


if __name__ == "__main__":
    EXAMPLE = """
# Paragraph

## Section

% block:

% table                     #{"A1":1, "A2": 2}

- test 1
- test 2


% row:
    % col:
        ### header

        1. Test
        2. Test 2
        3. Test 3
"""

    processor = IndentMarkdownProcessor()
    print(processor.convert(EXAMPLE))
