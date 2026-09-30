"""REST API client with automatic OAuth2 token refresh.

Provides a factory function that returns an authenticated HTTP request
function with automatic OAuth2 access token management.
"""

import logging
from collections.abc import Callable

import httpx

LOGGER = logging.getLogger("rest_client")

#: Default per-request timeout in seconds. Without one, a hung server blocks
#: the caller forever.
DEFAULT_TIMEOUT = 30.0

#: Module-level httpx helpers that have an equivalent ``Client`` method.
_METHOD_NAMES = frozenset(
    {"get", "post", "put", "patch", "delete", "head", "options", "stream", "send"}
)


def get_rest_client(base_url: str, refresh_token: str) -> Callable:
    """
    Returns a REST client function that handles OAuth2 authentication.

    Args:
        base_url (str): The base URL for the API.
        refresh_token (str): The refresh token for OAuth2 authentication.

    Returns:
        Callable: A function that can be used to make authenticated HTTP requests.
    """
    tokens: dict[str, str] = {"refresh_token": refresh_token}
    # One client per returned callable: keeps connections pooled and gives
    # every call a bounded timeout.
    client = httpx.Client(timeout=DEFAULT_TIMEOUT)

    def _call(method: Callable, url: str, *args, **kwargs) -> httpx.Response:
        """Dispatch *method* through the pooled client.

        Callers pass the module-level ``httpx.get``/``httpx.post``/... function,
        so map it onto the equivalent client method to benefit from pooling.
        """
        name = getattr(method, "__name__", "")
        if name in _METHOD_NAMES and hasattr(client, name):
            return getattr(client, name)(url, *args, **kwargs)
        return method(client, url, *args, **kwargs)

    def _oauth2_httpx(
        httpx_method: Callable, relative_url: str, *args, **kwargs
    ) -> httpx.Response | None:
        """
        Internal function to handle OAuth2 authentication and make HTTP requests.

        Args:
            httpx_method (Callable): The HTTP method to use (e.g., httpx.get, httpx.post).
            relative_url (str): The relative URL for the API endpoint.
            *args: Additional positional arguments for the HTTP request.
            **kwargs: Additional keyword arguments for the HTTP request.

        Returns:
            Optional[httpx.Response]: The HTTP response, or None if an error occurs.
        """
        nonlocal tokens, base_url

        kwargs.setdefault("timeout", DEFAULT_TIMEOUT)

        # Add authorization header if access token is available
        if "access_token" in tokens:
            authorization = f"Bearer {tokens['access_token']}"
            # Copy: the caller's headers dict must not be mutated in place.
            headers = dict(kwargs.get("headers") or {})
            headers["Authorization"] = authorization
            kwargs["headers"] = headers

            try:
                response = _call(httpx_method, base_url + relative_url, *args, **kwargs)
                if response.status_code != 401:
                    return response
            except httpx.HTTPError as e:
                # raise_for_status() raises HTTPStatusError, a subclass of
                # HTTPError but not of RequestError.
                LOGGER.error("Request failed: %s", e)
                return None

        # If access token is not available or request is unauthorized, refresh the token
        try:
            headers = {
                "Authorization": f"Basic {tokens['refresh_token']}",
                "Cache-Control": "no-cache",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            token_response = client.post(
                f"{base_url}/o/token/",
                headers=headers,
                data={"grant_type": "client_credentials"},
                timeout=DEFAULT_TIMEOUT,
            )
            token_response.raise_for_status()
            tokens["access_token"] = token_response.json()["access_token"]

            # Retry the original request with the new access token
            authorization = f"Bearer {tokens['access_token']}"
            headers = dict(kwargs.get("headers") or {})
            headers["Authorization"] = authorization
            kwargs["headers"] = headers

            return _call(httpx_method, base_url + relative_url, *args, **kwargs)
        except httpx.HTTPError as e:
            LOGGER.error("Token refresh failed: %s", e)
            return None

    return _oauth2_httpx


if __name__ == "__main__":
    # Example usage
    MP = 1
    # Example value only - do not put a real refresh token in source control.
    refresh_token = "REFRESH_TOKEN_HERE"
    client = get_rest_client("http://127.0.0.1:8000", refresh_token)

    # Delete a measurement
    endpoint = f"/api/otkernel/{MP}/measurement/"
    response = client(httpx.delete, endpoint)
    if response:
        print(response.status_code)
        print(response.json())

    # Post new measurements
    for i in range(100):
        data = {"data": {"hight": 20 + i}}
        response = client(httpx.post, endpoint, json=data)
        if response:
            print(response.json())
