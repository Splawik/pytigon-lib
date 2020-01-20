from cefpython3 import cefpython as cef
import platform
import sys
import time
import http.client
import asyncio
import json

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


async def run_async(url, title="Pytigon", parent_win = None, x=200, y=200, width=1024, height=768):
    close = False
    
    class LifespanHandler(object):
        def OnBeforeClose(self, browser):
            nonlocal close 
            close = True

    class JSBridge:
        def __init__(self, eval_events):
            self.results = {}
            self.eval_events = eval_events

        def return_result(self, result, uid):
            self.results[uid] = json.loads(result) if result else None
            self.eval_events[uid].set()

        def call(self, func_name, param, value_id):
            js_bridge_call(self.window, func_name, param, value_id)

    async def loop():
        nonlocal close 
        while not close:
            cef.MessageLoopWork()

    info = cef.WindowInfo()
    if parent_win:
        info.SetAsChild(self.Handle, [x, y, x + width, y + height])
    else:
        info.SetAsChild(0, [x, y, x + width, y + height])

    while True:
        test = exists(url)
        if test:
            print("Wait")
            break
        else:
            time.sleep(1)
            print("Sleep")

    browser = cef.CreateBrowserSync(window_info=info, url=url, window_title=title)
    browser.SetClientHandler(LifespanHandler())

    bindings = cef.JavascriptBindings()
    bindings.SetObject('external', browser.js_bridge)

    bindings.SetFunction('alert', alert_func)

    await loop()


def run(url, title="Pytigon", parent_win = None, x=200, y=200, width=1024, height=768):
    check_versions()
    sys.excepthook = cef.ExceptHook
    cef.Initialize()
    asyncio.run(run_async(url, title, parent_win, x, y, width, height))
    cef.Shutdown()
