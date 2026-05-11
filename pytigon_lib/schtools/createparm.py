from urllib.parse import urlencode
from typing import Any, Dict, List, Optional, Tuple, Union


class DictParm:
    """A container for dictionary-based parameters with safe access methods.

    Wraps a dict and provides checked get/query operations to avoid
    scattered KeyError handling in calling code.
    """

    def __init__(self, data: Dict[str, Any]) -> None:
        """Initialize with a parameter dictionary.

        Args:
            data: Dictionary mapping parameter names to values.
        """
        self.data = data

    def get_parm(self, param: str) -> Any:
        """Get a parameter value, raising KeyError if missing.

        Args:
            param: The parameter name to retrieve.

        Returns:
            The parameter value.

        Raises:
            KeyError: If the parameter is not found in the dictionary.
        """
        if param not in self.data:
            raise KeyError(f"Parameter '{param}' not found.")
        return self.data[param]

    def has_parm(self, param: str) -> bool:
        """Check whether a parameter exists in the dictionary.

        Args:
            param: The parameter name to check.

        Returns:
            True if the parameter exists, False otherwise.
        """
        return param in self.data


def convert_param(param: Any) -> Union[str, List, bool]:
    """Convert a parameter value to a format suitable for URL encoding.

    - Objects with class name 'DateTime' are truncated to first 10 chars.
    - Lists and booleans are returned as-is.
    - Everything else is converted to str.

    Args:
        param: The value to convert.

    Returns:
        A URL-encoding-friendly representation.
    """
    if hasattr(param, "__class__") and type(param).__name__ == "DateTime":
        return str(param)[:10]
    if isinstance(param, (list, bool)):
        return param
    return str(param)


def dict_from_param(param: DictParm, fields: List[str]) -> Dict[str, Any]:
    """Build a dictionary from selected fields present in a DictParm.

    Args:
        param: The DictParm instance to read from.
        fields: List of field names to extract.

    Returns:
        A dictionary containing only the fields that exist in param.
    """
    return {field: param.get_parm(field) for field in fields if param.has_parm(field)}


def create_parm(
    address: str, dic: DictParm, no_encode: bool = False
) -> Optional[Tuple[str, str, Union[Dict, str]]]:
    """Parse an address string and build URL parameters from a DictParm.

    The address format is: ``base_url|param1,param2,param3``
    Parameters with ``__`` suffix are grouped under a common base name,
    enabling multiple values for the same parameter (e.g. ``filter__by_date``).

    Args:
        address: The address string containing base URL and parameter names.
        dic: The DictParm providing parameter values.
        no_encode: If True, returns the raw dict instead of a URL-encoded string.

    Returns:
        A tuple of (base_url, separator, parameters) where parameters is
        either a dict or a URL-encoded string, or None if no parameters
        are defined in the address.
    """
    if not address:
        return None

    parts = address.split("|")
    if len(parts) <= 1:
        return None

    params = parts[1].split(",")
    separator = "&" if "?" in address else "?"
    encoded_params = {}

    for param in params:
        if not param:
            continue
        if dic.has_parm(param):
            value = dic.get_parm(param)
            if value is None:
                continue
            if "__" in param:
                base_param = param.split("__")[0]
                converted = convert_param(value)
                if base_param in encoded_params:
                    existing = encoded_params[base_param]
                    if isinstance(existing, list):
                        existing.append(converted)
                    else:
                        encoded_params[base_param] = [existing, converted]
                else:
                    encoded_params[base_param] = converted
            else:
                encoded_params[param] = convert_param(value)

    if no_encode:
        return parts[0], separator, encoded_params
    else:
        return parts[0], separator, urlencode(encoded_params, doseq=True)


def create_post_param(address: str, dic: DictParm) -> Tuple[str, Dict[str, Any]]:
    """Parse an address string and build POST parameters from a DictParm.

    Args:
        address: The address string (same format as create_parm).
        dic: The DictParm providing parameter values.

    Returns:
        A tuple of (base_url, parameters_dict). If no parameters are
        defined in the address, returns (address, empty_dict).
    """
    parts = address.split("|")
    if len(parts) > 1:
        params = parts[1].split(",")
        return parts[0], dict_from_param(dic, params)
    return parts[0], {}
