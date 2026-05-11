"""Utility to generate an OAuth2 refresh token from client credentials.

Usage: python -m pytigon_lib.schhttptools.get_oauth2_refresh_token
"""

import base64
import sys


def get_refresh_token(client_id: str, client_secret: str) -> str:
    """Generate a Base64-encoded refresh token from client ID and secret.

    The token is created by Base64-encoding the 'client_id:client_secret' pair,
    following the OAuth2 Basic authentication scheme.

    Args:
        client_id: The OAuth2 client ID.
        client_secret: The OAuth2 client secret.

    Returns:
        Base64-encoded refresh token string.

    Raises:
        ValueError: If the credentials cannot be encoded.
    """
    if not client_id or not client_secret:
        raise ValueError("Client ID and Client Secret cannot be empty.")
    try:
        credential = f"{client_id}:{client_secret}"
        refresh_token = base64.b64encode(credential.encode("utf-8")).decode("utf-8")
        return refresh_token
    except (UnicodeEncodeError, UnicodeDecodeError) as e:
        raise ValueError(f"Error encoding refresh token: {e}") from e


def main():
    """Read client credentials from stdin and print the refresh token."""
    try:
        print("Enter client id: ", file=sys.stderr)
        client_id = input().strip()
        print("Enter client secret: ", file=sys.stderr)
        client_secret = input().strip()

        refresh_token = get_refresh_token(client_id, client_secret)
        print(refresh_token)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except EOFError:
        print("Error: No input provided.", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
