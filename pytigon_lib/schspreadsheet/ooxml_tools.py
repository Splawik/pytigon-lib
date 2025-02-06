from lxml import etree


def make_update_filter_fun(cache_field_name, pivot_table_name, pivot_field_name, value):
    """Create a filter function to update pivot table based on cache field value.

    Args:
        cache_field_name (str): Name of the cache field.
        pivot_table_name (str): Name of the pivot table.
        pivot_field_name (str): Name of the pivot field.
        value (str): Value to filter on.

    Returns:
        function: A function that updates the pivot table based on the cache field value.
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
                id = tab.index(value)
            except ValueError:
                id = -1

            if id >= 0:
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
                                if int(item.attrib["x"]) == id:
                                    item.attrib.pop("h", None)
                                else:
                                    item.attrib["h"] = "1"
                        break

                # Add to update list if not from cache
                if not ret["from_cache"]:
                    doc_transform.to_update.append((pivot_table_name, root2))

        except Exception as e:
            raise RuntimeError(f"Error updating filter: {e}")

        return False

    return _update_filter


def make_group_fun(pivot_field_no, values_on):
    """Create a grouping function for pivot fields.

    Args:
        pivot_field_no (int): Index of the pivot field.
        values_on (str): Semicolon-separated values to group on.

    Returns:
        function: A function that updates the pivot field grouping.
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

        except Exception as e:
            raise RuntimeError(f"Error updating group: {e}")

        return True

    return _update_group
