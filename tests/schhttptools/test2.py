from pytigon.django_min_init import init
from pytigon_lib.schhttptools.httpclient import HttpClient
from pytigon_lib.schhttptools.rest_client import get_rest_client
import httpx


def update_settings(settings):
    settings.SECRET_KEY = "anawa"


init(
    prj="schpytigondemo",
    pytigon_standard=True,
    embeded_django=True,
    settings_callback=update_settings,
)

# client = HttpClient()


refresh_token = "bXhtM29qMDRQVGt5UjVHbGRhQm1TNDMwVU5USkNZdFdYVUo5QUFiOTowbzFiODFPVkh2OUZDQXdPTEhQQXN6WUc2bUxIb3ZlelVMb0ZZZk5sT1BJb2NxRGhsQjZlakVjSzI3anBOZUpSN0VXeGdBTXVWeldDZlpHbnJ4eHV2MVRPcDcyc1NIOXBqN3paWG53aTR6d3dVSmZUSVdpQlo2UHhxeGZFS05iRA=="
client = get_rest_client("http://127.0.0.1:8000", refresh_token)
# client = get_rest_client("http://127.0.0.2", refresh_token)

endpoint = "/api/tables_adv_demo/hello"
ret = client(httpx.get, endpoint)
print(ret.status_code)
ret2 = ret.json()
print(ret2)
