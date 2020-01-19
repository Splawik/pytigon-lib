# Hello world example. Doesn't depend on any third party GUI framework.
# Tested with CEF Python v57.0+.

from cefpython3 import cefpython as cef
import platform
import sys
import time
import http.client

def exists(site, path="/"):
    try:
        print("A1", site)
        conn = http.client.HTTPConnection(site.split("//")[1])
        print("A2")
        conn.request("HEAD", path)
        response = conn.getresponse()
        conn.close()
        return response.status == 200
    except:
        False

def check_versions():
    ver = cef.GetVersion()
    print("[pytigon] CEF Python {ver}".format(ver=ver["version"]))
    print("[pytigon] Chromium {ver}".format(ver=ver["chrome_version"]))
    print("[pytigon] CEF {ver}".format(ver=ver["cef_version"]))
    print(
        "[pytigon] Python {ver} {arch}".format(
            ver=platform.python_version(), arch=platform.architecture()[0]
        )
    )
    assert cef.__version__ >= "57.0", "CEF Python v57.0+ required to run this"


def run(url, title="Pytigon", x=200, y=200, width=1024, height=768):
    check_versions()
    sys.excepthook = cef.ExceptHook  # To shutdown all CEF processes on error
    cef.Initialize()

    info = cef.WindowInfo()
    info.SetAsChild(0, [x, y, x + width, y + height])

    while True:
        test = exists(url)
        if test:
            print("Wait")
            break
        else:
            time.sleep(1)
            print("Sleep")

    cef.CreateBrowserSync(window_info=info, url=url, window_title=title)
    cef.MessageLoop()
    cef.Shutdown()

