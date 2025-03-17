import base64
import sys


def get_refresh_token(client_id: str, client_secret: str) -> str:
    """
    Generates a refresh token using the provided client ID and client secret.

    Args:
        client_id (str): The client ID.
        client_secret (str): The client secret.

    Returns:
        str: The base64 encoded refresh token.
    """
    try:
        credential = f"{client_id}:{client_secret}"
        refresh_token = base64.b64encode(credential.encode("utf-8")).decode("utf-8")
        return refresh_token
    except Exception as e:
        raise ValueError(f"Error generating refresh token: {e}")


def main():
    """
    Main function to get client ID and client secret from user input and print the refresh token.
    """
    try:
        print("Enter client id: ", file=sys.stderr)
        client_id = input().strip()
        print("Enter client secret: ", file=sys.stderr)
        client_secret = input().strip()

        if not client_id or not client_secret:
            raise ValueError("Client ID and Client Secret cannot be empty.")

        refresh_token = get_refresh_token(client_id, client_secret)
        print(refresh_token)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
