class MakeTreeFromObject:
    """Generate a tree widget based on a Django model."""

    def __init__(self, model, callback, field_name=None):
        """Initialize the tree generator.

        Args:
            model: Django model to generate the tree from.
            callback: Function to retrieve tree node details.
                The callback function should accept two arguments:
                    - id: Determines what information to return.
                        - 0: Return True if the object has children, False otherwise.
                        - 1: Return the name of the object.
                        - 2: Return a list of actions for the object.
                    - obj: The object to query.
            field_name: Optional name of the tree field.
        """
        self.model = model
        self.callback = callback
        self.field_name = field_name

    def _tree_from_object_children(self, parent):
        """Generate HTML for child nodes of a given parent node.

        Args:
            parent: The parent node object.

        Returns:
            str: HTML string representing the child nodes.
        """
        children = self.model.objects.filter(parent=parent)
        ret = ""
        for child in children:
            if self.callback(0, child):
                ret += "<li>"
                ret += f"<span class='folder'>{self.callback(1, child)}</span>"
                ret += "<ul>"
                actions = self.callback(2, child)
                for action in actions:
                    link, name = action
                    ret += f"<li><span class='file'><a href='{link}'>{name}</a></span></li>"
                ret += self._tree_from_object_children(child)
                ret += "</ul>"
                ret += "</li>"
        return ret.replace("<ul></ul>", "")

    def _tree_from_object(self):
        """Generate HTML for the root nodes of the tree.

        Returns:
            str: HTML string representing the root nodes.
        """
        root_nodes = self.model.objects.filter(parent=None)
        ret = ""
        for node in root_nodes:
            if self.callback(0, node):
                ret += "<li>"
                ret += f"<span class='folder'>{self.callback(1, node)}</span>"
                ret += "<ul>"
                actions = self.callback(2, node)
                for action in actions:
                    link, name = action
                    ret += f"<li><span class='file'><a href='{link}'>{name}</a></span></li>"
                ret += self._tree_from_object_children(node)
                ret += "</ul>"
                ret += "</li>"
        return ret

    def _gen(self, head_ctrl, end_head_ctrl):
        """Generate the final HTML structure.

        Args:
            head_ctrl: HTML to prepend to the tree.
            end_head_ctrl: HTML to append to the tree.

        Returns:
            str: The complete HTML structure.
        """
        try:
            if self.field_name:
                ret = f"{head_ctrl}<li><span class='folder'>{self.field_name}</span><ul>{self._tree_from_object()}</ul></li>{end_head_ctrl}"
            else:
                ret = f"{head_ctrl}{self._tree_from_object()}{end_head_ctrl}"
        except Exception as e:
            import sys
            import traceback

            print(f"Error: {e}", file=sys.stderr)
            traceback.print_exc()
            ret = ""
        return ret

    def gen_html(self):
        """Generate and return HTML for the tree widget.

        Returns:
            str: HTML string for the tree widget.
        """
        return self._gen("<ul id='browser' class='filetree'>", "</ul>")

    def gen_shtml(self):
        """Generate and return simplified HTML for the tree widget.

        Returns:
            str: Simplified HTML string for the tree widget.
        """
        return self._gen("", "")
