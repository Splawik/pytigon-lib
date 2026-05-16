"""Tree widget generation for the schviews module.

Provides a class that generates HTML tree widgets from Django model
hierarchies using a callback-based pattern for node rendering.
"""

import html
import logging
from collections.abc import Callable
from typing import Any, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Type alias for the callback: f(query_id: int, obj: Any) -> Any
TreeCallback = Callable[[int, Any], Any]

# -- String constants to reduce repeated allocations -----------------------
_UL_END = "</ul>"
_LI_END = "</li>"


class MakeTreeFromObject:
    """Generate an HTML tree widget from a Django model hierarchy.

    The tree is built by traversing parent/child relationships on the
    model. A user-provided callback controls what information is shown
    for each node (name, has-children flag, actions).

    Example usage::

        tree = MakeTreeFromObject(MyModel, my_callback, field_name="Root")
        html_fragment = tree.gen_html()
    """

    def __init__(
        self,
        model: Any,
        callback: TreeCallback,
        field_name: Optional[str] = None,
    ) -> None:
        """Initialize the tree generator.

        Args:
            model: Django model class with a ``parent`` ForeignKey field.
            callback: Function to retrieve tree node details. Called with
                two arguments:

                - ``query_id`` (int):
                    - 0: Return ``True`` if the object has children, ``False`` otherwise.
                    - 1: Return the display name of the object (as a string).
                    - 2: Return a list of ``(link, name)`` action tuples.
                - ``obj``: The model instance being queried.

            field_name: Optional label displayed as the root folder name.
        """
        self.model = model
        self.callback = callback
        self.field_name = field_name

    # -- Private helpers ---------------------------------------------------

    @staticmethod
    def _build_node_html(
        label: str,
        actions: List[Tuple[str, str]],
        children_html: str,
    ) -> str:
        """Build the HTML fragment for a single tree node.

        Args:
            label: The *already-escaped* display name of the node.
            actions: List of ``(link, name)`` tuples for node actions.
            children_html: Pre-rendered HTML for child nodes.

        Returns:
            An HTML string representing the node and its subtree.
        """
        parts = ["<li>"]
        parts.append(f"<span class='folder'>{html.escape(label, quote=True)}</span>")
        parts.append("<ul>")
        for link, name in actions:
            parts.append(
                "<li><span class='file'>"
                f"<a href='{html.escape(link, quote=True)}'>"
                f"{html.escape(name, quote=True)}"
                "</a></span></li>"
            )
        parts.append(children_html)
        parts.append(_UL_END)
        parts.append(_LI_END)
        return "".join(parts)

    def _tree_from_object_children(self, parent: Any) -> str:
        """Recursively generate HTML for child nodes of a parent.

        Args:
            parent: The parent model instance.

        Returns:
            HTML string for the subtree rooted at *parent*.
        """
        try:
            children = self.model.objects.filter(parent=parent)
        except Exception:
            logger.exception(
                "Error querying children for parent id=%s",
                getattr(parent, "pk", "?"),
            )
            return ""

        parts = []
        for child in children:
            try:
                if self.callback(0, child):
                    label = str(self.callback(1, child))
                    actions = self.callback(2, child) or []
                    children_html = self._tree_from_object_children(child)
                    parts.append(self._build_node_html(label, actions, children_html))
            except Exception:
                logger.exception(
                    "Error processing tree node id=%s",
                    getattr(child, "pk", "?"),
                )
        result = "".join(parts)
        # Remove empty <ul> elements to keep the markup clean.
        return result.replace("<ul></ul>", "")

    def _tree_from_object(self) -> str:
        """Generate HTML for the root nodes of the tree.

        Returns:
            HTML string for all root-level nodes.
        """
        try:
            root_nodes = self.model.objects.filter(parent=None)
        except Exception:
            logger.exception("Error querying root nodes for model %s", self.model)
            return ""

        parts = []
        for node in root_nodes:
            try:
                if self.callback(0, node):
                    label = str(self.callback(1, node))
                    actions = self.callback(2, node) or []
                    children_html = self._tree_from_object_children(node)
                    parts.append(self._build_node_html(label, actions, children_html))
            except Exception:
                logger.exception(
                    "Error processing root tree node id=%s",
                    getattr(node, "pk", "?"),
                )
        return "".join(parts)

    def _gen(self, head_ctrl: str, end_head_ctrl: str) -> str:
        """Assemble the final HTML structure around the tree.

        Args:
            head_ctrl: HTML to prepend before the tree
                (e.g. ``<ul id='browser' class='filetree'>``).
            end_head_ctrl: HTML to append after the tree
                (e.g. ``</ul>``).

        Returns:
            The complete HTML structure, or an empty string on error.
        """
        try:
            if self.field_name:
                ret = (
                    f"{head_ctrl}<li>"
                    f"<span class='folder'>"
                    f"{html.escape(self.field_name, quote=True)}"
                    f"</span>"
                    f"<ul>{self._tree_from_object()}</ul></li>"
                    f"{end_head_ctrl}"
                )
            else:
                ret = f"{head_ctrl}{self._tree_from_object()}{end_head_ctrl}"
        except Exception:
            logger.exception("Error generating tree HTML")
            ret = ""
        return ret

    # -- Public API --------------------------------------------------------

    def gen_html(self) -> str:
        """Generate and return HTML for a full tree widget.

        The output is wrapped in ``<ul id='browser' class='filetree'>``.

        Returns:
            HTML string for the tree widget.
        """
        return self._gen("<ul id='browser' class='filetree'>", "</ul>")

    def gen_shtml(self) -> str:
        """Generate and return simplified HTML for a tree widget.

        The output has no outer wrapping element — useful for embedding
        the tree within an existing list.

        Returns:
            Simplified HTML string for the tree widget.
        """
        return self._gen("", "")
