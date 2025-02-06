import httpx
from typing import Dict, Any, Callable, Optional


def get_rest_client(base_url: str, refresh_token: str) -> Callable:
    """
    Returns a REST client function that handles OAuth2 authentication.

    Args:
        base_url (str): The base URL for the API.
        refresh_token (str): The refresh token for OAuth2 authentication.

    Returns:
        Callable: A function that can be used to make authenticated HTTP requests.
    """
    tokens: Dict[str, str] = {"refresh_token": refresh_token}

    def _oauth2_httpx(
        httpx_method: Callable, relative_url: str, *args, **kwargs
    ) -> Optional[httpx.Response]:
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

        # Add authorization header if access token is available
        if "access_token" in tokens:
            authorization = f"Bearer {tokens['access_token']}"
            headers = kwargs.get("headers", {})
            headers["Authorization"] = authorization
            kwargs["headers"] = headers

            try:
                response = httpx_method(base_url + relative_url, *args, **kwargs)
                if response.status_code != 401:
                    return response
            except httpx.RequestError as e:
                print(f"Request failed: {e}")
                return None

        # If access token is not available or request is unauthorized, refresh the token
        try:
            headers = {
                "Authorization": f"Basic {tokens['refresh_token']}",
                "Cache-Control": "no-cache",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            token_response = httpx.post(
                f"{base_url}/o/token/",
                headers=headers,
                data={"grant_type": "client_credentials"},
            )
            token_response.raise_for_status()
            tokens["access_token"] = token_response.json()["access_token"]

            # Retry the original request with the new access token
            authorization = f"Bearer {tokens['access_token']}"
            headers = kwargs.get("headers", {})
            headers["Authorization"] = authorization
            kwargs["headers"] = headers

            return httpx_method(base_url + relative_url, *args, **kwargs)
        except httpx.RequestError as e:
            print(f"Token refresh failed: {e}")
            return None

    return _oauth2_httpx


if __name__ == "__main__":
    # Example usage
    MP = 1
    refresh_token = "TER3N3NaQnA5blQ2dUtKd01sRHMwODl1TGRlT2JLd0laaTJIM0xGQTpoelphZmVudmhidjVTek1MUWx2eDNiY2pTOUlRdDlOSVk0RjRaallEOUJiSnI3V1VaZkw1dnFFWGlBdElHaks3WTB1MHBoUXVEVE90UllWZjZLMTBkODR1REN4RjZhbEdnRVFZcGsxelBySVB1Mk1TSkw3dWRTc2hQU0Mxd29mNw=="
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
