import time


class Window:
    def __init__(self, proxy, selector):
        self.proxy = proxy
        self.win_id = proxy.findwindow(selector)
        print("Window: ", self.win_id, selector)

    def setpointer(self):
        self.proxy.setpointer(self.win_id)
        return self

    def click(self):
        self.proxy.click(self.win_id)
        return self

    def setfocus(self):
        self.proxy.setfocus(self.win_id)
        return self

    def clickbarbutton(self, title, move_pointer=True):
        x = self.proxy.gettoolbarbutton(self.win_id, title)
        print("x: ", x)
        print("title:", title)
        print(self.win_id)
        if move_pointer:
            self.proxy.setpointer(self.win_id, (x[0] + 30, x[1] + 30))
        self.proxy.clickbarbutton(self.win_id, title)
        return self

    def setvalue(self, value):
        self.proxy.setvalue(self.win_id, value)
        return self

    def pause(self, seconds):
        time.sleep(seconds)
