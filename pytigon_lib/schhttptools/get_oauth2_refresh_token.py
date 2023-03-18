import base64
import httpx
import json
import sys

"""
Create app: {{base_url}}//o/applications/
Client type: confidential
Authorization Grant Type: client-credentials
Redirect Uris: Empty

Read Client ID and Client secret before saving
"""


def get_refresh_token(client_id, client_secret):
    credential = "{0}:{1}".format(client_id, client_secret)
    refresh_token = base64.b64encode(credential.encode("utf-8")).decode("utf-8")
    return refresh_token


if __name__ == "__main__":
    print("Enter client id: ", file=sys.stderr)
    client_id = input()
    print("Enter client secret: ", file=sys.stderr)
    client_secret = input()
    print(get_refresh_token(client_id, client_secret))
