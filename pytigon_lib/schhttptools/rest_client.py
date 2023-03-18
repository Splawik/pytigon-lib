import httpx


def get_rest_client(base_url, refresh_token):
    tokens = {"refresh_token": refresh_token}

    def _oauth2_httpx(httpx_method, relative_url, *argi, **argv):
        nonlocal tokens, base_url
        if "access_token" in tokens:
            authorization = "Bearer %s" % tokens["access_token"]
            if "headers" in argv:
                argv["headers"]["Authorization"] = authorization
            else:
                argv["headers"] = {"Authorization": authorization}

            ret = httpx_method(base_url + relative_url, *argi, **argv)
        else:
            ret = None
        if not ret or ret.status_code == 401:
            headers = {
                "Authorization": "Basic %s" % tokens["refresh_token"],
                "Cache-Control": "no-cache",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            ret = httpx.post(
                "%s/o/token/" % base_url,
                headers=headers,
                data={"grant_type": "client_credentials"},
            ).json()
            tokens["access_token"] = ret["access_token"]
            if "headers" in argv:
                authorization = "Bearer %s" % tokens["access_token"]
                argv["headers"]["Authorization"] = authorization
                return httpx_method(base_url + relative_url, *argi, **argv)
            else:
                return _oauth2_httpx(httpx_method, relative_url, *argi, **argv)
        else:
            return ret

    return _oauth2_httpx


if __name__ == "__main__":
    MP = 1
    refresh_token = "TER3N3NaQnA5blQ2dUtKd01sRHMwODl1TGRlT2JLd0laaTJIM0xGQTpoelphZmVudmhidjVTek1MUWx2eDNiY2pTOUlRdDlOSVk0RjRaallEOUJiSnI3V1VaZkw1dnFFWGlBdElHaks3WTB1MHBoUXVEVE90UllWZjZLMTBkODR1REN4RjZhbEdnRVFZcGsxelBySVB1Mk1TSkw3dWRTc2hQU0Mxd29mNw=="
    client = get_rest_client("http://127.0.0.1:8000", refresh_token)

    endpoint = "/api/otkernel/%d/measurement/" % MP
    ret = client(httpx.delete, endpoint)
    print(ret.status_code)
    ret2 = ret.json()
    print(ret2)

    endpoint = "/api/otkernel/%d/measurement/" % MP
    for i in range(0, 100):
        data = {"data": {"hight": 20 + i}}
        print(client(httpx.post, endpoint, json=data).json())
