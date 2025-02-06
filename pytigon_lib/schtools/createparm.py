from urllib.parse import urlencode
from typing import Any, Dict, List, Optional, Tuple, Union


class DictParm:
    """A class to handle dictionary parameters."""

    def __init__(self, data: Dict[str, Any]) -> None:
        """Initialize with a dictionary."""
        self.data = data

    def get_parm(self, param: str) -> Any:
        """Get a parameter from the dictionary."""
        if param not in self.data:
            raise KeyError(f"Parameter '{param}' not found in dictionary.")
        return self.data[param]

    def has_parm(self, param: str) -> bool:
        """Check if a parameter exists in the dictionary."""
        return param in self.data


def convert_param(param: Any) -> Union[str, List, bool]:
    """Convert a parameter to a suitable format for URL encoding."""
    if hasattr(param, "__class__") and param.__class__.__name__ == "DateTime":
        return str(param)[:10]
    if isinstance(param, (list, bool)):
        return param
    return str(param)


def dict_from_param(param: DictParm, fields: List[str]) -> Dict[str, Any]:
    """Create a dictionary from a list of fields using the given DictParm object."""
    return {field: param.get_parm(field) for field in fields if param.has_parm(field)}


def create_parm(
    address: str, dic: DictParm, no_encode: bool = False
) -> Optional[Tuple[str, str, Union[Dict, str]]]:
    """Create parameters from the address and dictionary."""
    parts = address.split("|")
    if len(parts) <= 1:
        return None

    params = parts[1].split(",")
    separator = "&" if "?" in address else "?"
    encoded_params = {}

    for param in params:
        if dic.has_parm(param):
            value = dic.get_parm(param)
            if value is not None:
                if "__" in param:
                    base_param = param.split("__")[0]
                    if base_param in encoded_params:
                        if isinstance(encoded_params[base_param], list):
                            encoded_params[base_param].append(convert_param(value))
                        else:
                            encoded_params[base_param] = [
                                encoded_params[base_param],
                                convert_param(value),
                            ]
                    else:
                        encoded_params[base_param] = convert_param(value)
                else:
                    encoded_params[param] = convert_param(value)

    if no_encode:
        return parts[0], separator, encoded_params
    else:
        return parts[0], separator, urlencode(encoded_params, doseq=True)


def create_post_param(address: str, dic: DictParm) -> Tuple[str, Dict[str, Any]]:
    """Create POST parameters from the address and dictionary."""
    parts = address.split("|")
    if len(parts) > 1:
        params = parts[1].split(",")
        return parts[0], dict_from_param(dic, params)
    return parts[0], {}
