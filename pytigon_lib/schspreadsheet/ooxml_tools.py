"""
OOXML pivot table manipulation utilities.

Provides factory functions that create callbacks for filtering and
grouping pivot table data within OOXML spreadsheet transformations.
These are used as extended transformation scripts by OOXmlDocTransform.
"""

import logging

logger = logging.getLogger(__name__)


def make_update_filter_fun(cache_field_name, pivot_table_name, pivot_field_name, value):
    """Create a filter function that updates a pivot table based on a cache field value.

    Returns a callable suitable for use as an extended transformation script.
    When invoked, it searches the pivot cache for a matching field value,
    then hides all pivot items except the matched one.

    Args:
        cache_field_name: Name of the cache field to search.
        pivot_table_name: XML path to the pivot table definition.
        pivot_field_name: Name of the pivot field to update.
        value: Value to select in the filter.

    Returns:
        A callable with signature ``(doc_transform, root) -> bool``
        that returns False (no upstream changes needed).
    """

    def _update_filter(doc_transform, root):
        try:
            # Find all cache fields
            fields = root.findall(".//cacheFields/cacheField", namespaces=root.nsmap)
            tab = []
            for field in fields:
                if field.attrib.get("name") == cache_field_name:
                    shared_items = field.findall(
                        ".//sharedItems", namespaces=root.nsmap
                    )
                    for item in shared_items:
                        for sub_item in item:
                            tab.append(sub_item.attrib.get("v", ""))
                    break

            # Find the index of the value in the cache field
            try:
                idx = tab.index(value)
            except ValueError:
                idx = -1

            if idx >= 0:
                # Get the pivot table content
                ret = doc_transform.get_xml_content(pivot_table_name)
                root2 = ret["data"]
                fields2 = root2.findall(
                    ".//pivotFields/pivotField", namespaces=root2.nsmap
                )

                # Update the pivot field items based on the cache field value
                for field2 in fields2:
                    if field2.attrib.get("name") == pivot_field_name:
                        items = field2.findall(".//items/item", namespaces=root2.nsmap)
                        for item in items:
                            if "x" in item.attrib:
                                if int(item.attrib["x"]) == idx:
                                    item.attrib.pop("h", None)
                                else:
                                    item.attrib["h"] = "1"
                        break

                # Add to update list if not from cache
                if not ret["from_cache"]:
                    doc_transform.to_update.append((pivot_table_name, root2))

        except Exception as e:
            logger.error("Error updating pivot filter: %s", e)
            raise RuntimeError(f"Error updating filter: {e}") from e

        return False

    return _update_filter


def make_group_fun(pivot_field_no, values_on):
    """Create a grouping function that shows/hides pivot field items.

    Returns a callable suitable for use as an extended transformation script.
    When invoked, it expands (shows) items whose names appear in the semicolon-
    separated list and collapses (hides) all others.

    Args:
        pivot_field_no: Zero-based index of the pivot field.
        values_on: Semicolon-separated names of items to show.

    Returns:
        A callable with signature ``(doc_transform, root) -> bool``
        that returns True (upstream content may need updating).
    """

    def _update_group(doc_transform, root):
        try:
            values_tab = values_on.split(";")
            fields = root.findall(".//pivotFields/pivotField", namespaces=root.nsmap)
            field = fields[pivot_field_no]
            items = field.findall(".//item", namespaces=root.nsmap)

            # Update the pivot field items based on the grouping values
            for item in items:
                if "n" in item.attrib and item.attrib["n"] in values_tab:
                    item.attrib.pop("sd", None)
                else:
                    item.attrib["sd"] = "0"

        except (IndexError, AttributeError, KeyError) as e:
            logger.error("Error updating pivot group: %s", e)
            raise RuntimeError(f"Error updating group: {e}") from e
        except Exception as e:
            logger.error("Unexpected error updating pivot group: %s", e)
            raise RuntimeError(f"Error updating group: {e}") from e

        return True

    return _update_group
