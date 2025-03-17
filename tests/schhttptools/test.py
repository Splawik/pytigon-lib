from pytigon.django_min_init import init
from pytigon_lib.schhttptools.httpclient import HttpClient

init(pytigon_standard=True, embeded_django=True)

client = HttpClient()
ret = client.get(None, "http://127.0.0.2/")
print(ret.str())
