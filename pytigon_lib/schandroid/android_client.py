import os
import sys
import socket
import fcntl
import struct
from os.path import expanduser
from kivy.app import App
from kivy.lang import Builder
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.animation import Animation
from kivy.properties import NumericProperty
from kivy.clock import Clock

try:
    from android.permissions import request_permissions, check_permission, Permission
except ImportError:
    request_permissions = None
    check_permission = None
    Permission = None
try:
    import netifaces
except ImportError:
    netifaces = None

# Constants
MAX_SEL_APP = 10
PERMISSIONS = [
    Permission.WRITE_EXTERNAL_STORAGE,
    Permission.READ_EXTERNAL_STORAGE,
    Permission.INTERNET,
    Permission.INSTALL_SHORTCUT,
    Permission.VIBRATE,
    Permission.ACCESS_WIFI_STATE,
    Permission.CHANGE_WIFI_STATE,
    Permission.ACCESS_NETWORK_STATE,
]

# Set up base path
BASE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
)
if BASE_PATH not in sys.path:
    sys.path.insert(0, BASE_PATH)
os.chdir(BASE_PATH)

# Initialize paths and settings
from pytigon_lib import init_paths

init_paths()
from pytigon.schserw import settings as schserw_settings
from pytigon_lib.schtools.install_init import init

if schserw_settings.PRJ_PATH not in sys.path:
    sys.path.append(schserw_settings.PRJ_PATH)

# Determine storage path
STORAGE = os.path.join(expanduser("~"), ".")
if "SECONDARY_STORAGE" in os.environ:
    p1 = os.path.join(os.environ["SECONDARY_STORAGE"], "pytigon_data")
    if os.path.exists(p1):
        STORAGE = p1[:-12]
if "EXTERNAL_STORAGE" in os.environ:
    p2 = os.path.join(os.environ["EXTERNAL_STORAGE"], "pytigon_data")
    if os.path.exists(p2):
        STORAGE = p2[:-12]

Builder.load_string(
    """
<InterfaceManager>:
    canvas.before:
        Color:
            rgba: 0.9, 0.9, 0.9, 1
        Rectangle:
            pos: self.pos
            size: self.size
        PushMatrix
        Rotate:
            angle: root.angle
            axis: 0, 0, 1
            origin: root.center
    canvas.after:
        PopMatrix
"""
)


class InterfaceManager(BoxLayout):
    angle = NumericProperty(0)

    def __init__(self, **kwargs):
        super(InterfaceManager, self).__init__(**kwargs)
        self.base_path = BASE_PATH
        self.webview = None
        self.app = None
        self.timer = None
        self.show_first_form()

    def show_first_form(self):
        ip_tab = self.get_ip_addresses()
        ip_address = ", ".join(ip_tab) if ip_tab else "-"

        label = Label(
            text=f"[size=18sp][color=88f][b]PYTIGON - select the application:[/b][/color][/size]\n[size=15sp][color=448](my ip addresses: {ip_address})[/b][/color][/size]",
            markup=True,
            halign="center",
        )
        self.add_widget(label)

        if not check_permission(Permission.WRITE_EXTERNAL_STORAGE):
            request_permissions(PERMISSIONS)

        init(
            "_schall",
            schserw_settings.ROOT_PATH,
            schserw_settings.DATA_PATH,
            schserw_settings.PRJ_PATH,
            schserw_settings.STATIC_ROOT,
            [schserw_settings.MEDIA_ROOT, schserw_settings.UPLOAD_PATH],
        )

        apps = self.get_available_apps()
        self.display_app_buttons(apps)

    def get_ip_addresses(self):
        ip_tab = []
        if netifaces:
            for interface in netifaces.interfaces():
                if interface[:2] in ("wl", "en", "et"):
                    ifaddress = netifaces.ifaddresses(interface)
                    if netifaces.AF_INET in ifaddress:
                        for inet in ifaddress[netifaces.AF_INET]:
                            if "addr" in inet:
                                addr = inet["addr"]
                                if len(addr.split(".")) == 4:
                                    ip_tab.append(addr)
        else:
            try:
                ip_address = self.get_ip_address(b"wlan0")
                ip_tab.append(ip_address)
            except Exception:
                pass
        return ip_tab

    def get_ip_address(self, ifname):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(
            fcntl.ioctl(s.fileno(), 0x8915, struct.pack(b"256s", ifname[:15]))[20:24]
        )

    def get_available_apps(self):
        base_apps_path = os.path.join(os.path.join(STORAGE, "pytigon"), "prj")
        apps = []
        for prj in os.listdir(base_apps_path):
            if not prj.startswith("_"):
                try:
                    x = __import__(prj + ".apps")
                    if hasattr(x.apps, "PUBLIC") and x.apps.PUBLIC:
                        apps.append(prj)
                except ImportError:
                    print(f"Error importing module: {prj}.apps")
        return apps

    def display_app_buttons(self, apps):
        if len(apps) > 1:
            dy = min(len(apps), MAX_SEL_APP) - 1
            for pos in apps[:dy]:
                button = Button(id=pos, text=pos, size_hint=(1, 1))
                button.bind(on_release=self.chose_callback)
                self.add_widget(button)

            if len(apps) > MAX_SEL_APP:
                spinner = Spinner(
                    text="Other applications",
                    values=apps[dy:],
                    size_hint=(0.5, 1),
                    pos_hint={"center_x": 0.5},
                )
                spinner.bind(text=self.spinner_callback)
                self.add_widget(spinner)
        elif apps:
            self.on_app_chosen(apps[0])
        else:
            self.on_app_chosen()

    def show_second_form(self):
        self.clear_widgets()
        self.img = Image(
            size_hint=(0.5, 0.5),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            source="loader.png",
        )
        self.add_widget(self.img)
        anim = Animation(angle=-360, duration=2)
        anim += Animation(angle=-360, duration=2)
        anim.repeat = True
        anim.start(self)

    def spinner_callback(self, spinner, text):
        self.on_app_chosen(text)

    def chose_callback(self, instance):
        self.on_app_chosen(instance.id)

    def on_app_chosen(self, app="schdevtools"):
        self.app = app

    def on_clock(self, dt):
        pass

    def create_webview(self):
        pass

    def on_page_finish(self, view, url):
        print(f"python:Pytigon:XXXXXX1 {url}")

    def on_fragment_finished(self):
        pass

    def on_angle(self, item, angle):
        if angle == -360:
            item.angle = 0


class PytigonApp(App):
    def build(self):
        self.bind(on_start=self.post_build_init)
        return InterfaceManager(orientation="vertical", padding=10, spacing=20)

    def post_build_init(self, ev):
        from kivy.base import EventLoop

        EventLoop.window.bind(on_keyboard=self.hook_keyboard)

    def hook_keyboard(self, window, key, *largs):
        pass

    def on_stop(self):
        print("python:Pytigon:on_stop")


if __name__ == "__main__":
    PytigonApp().run()
