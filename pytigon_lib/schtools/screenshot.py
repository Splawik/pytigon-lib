"""based on cefpython example: screenshot.py"""

import os
import platform
import subprocess
import sys
from PIL import Image

try:
    from cefpython3 import cefpython as cef
except ImportError:
    cef = None

_IMPORTED = False


def get_screenshot(url, size, img_path):
    """Capture a screenshot of the given URL and save it to the specified path.

    Args:
        url (str): The URL to capture.
        size (tuple): The dimensions of the screenshot (x, y, width, height).
        img_path (str): The path to save the screenshot.

    Raises:
        Exception: If the screenshot cannot be captured or saved.
    """
    global _IMPORTED
    if not _IMPORTED:
        _IMPORTED = True

    def create_browser(url):
        """Create a browser instance to load the URL.

        Args:
            url (str): The URL to load.
        """
        parent_window_handle = 0
        window_info = cef.WindowInfo()
        window_info.SetAsOffscreen(parent_window_handle)
        browser = cef.CreateBrowserSync(window_info=window_info, url=url)
        browser.SetClientHandler(LoadHandler())
        browser.SetClientHandler(RenderHandler())
        browser.SendFocusEvent(True)
        browser.WasResized()

    def save_screenshot(browser, path):
        """Save the screenshot to the specified path.

        Args:
            browser: The browser instance.
            path (str): The path to save the screenshot.

        Raises:
            Exception: If the buffer string is empty.
        """
        buffer_string = browser.GetUserData("OnPaint.buffer_string")
        if not buffer_string:
            raise Exception("buffer_string is empty, OnPaint never called?")
        image = Image.frombytes(
            "RGBA", (size[2], size[3]), buffer_string, "raw", "RGBA", 0, 1
        )
        image.save(path, "PNG")

    def exit_app(browser):
        """Close the browser and exit the application.

        Args:
            browser: The browser instance.
        """
        browser.CloseBrowser()
        cef.QuitMessageLoop()

    class LoadHandler(object):
        """Handle browser loading state changes."""

        def OnLoadingStateChange(self, browser, is_loading, **_):
            """Handle the loading state change event.

            Args:
                browser: The browser instance.
                is_loading (bool): Whether the browser is loading.
            """
            if not is_loading:
                save_screenshot(browser, img_path)
                cef.PostTask(cef.TID_UI, exit_app, browser)

        def OnLoadError(self, browser, frame, error_code, failed_url, **_):
            """Handle the load error event.

            Args:
                browser: The browser instance.
                frame: The frame that failed to load.
                error_code (int): The error code.
                failed_url (str): The URL that failed to load.
            """
            if not frame.IsMain():
                return
            cef.PostTask(cef.TID_UI, exit_app, browser)

    class RenderHandler(object):
        """Handle rendering events."""

        def __init__(self):
            """Initialize the RenderHandler."""
            self.OnPaint_called = False

        def GetViewRect(self, rect_out, **_):
            """Get the view rectangle.

            Args:
                rect_out: The output rectangle.

            Returns:
                bool: True if successful.
            """
            rect_out.extend((size[0], size[1], size[2], size[3]))
            return True

        def OnPaint(self, browser, element_type, paint_buffer, **_):
            """Handle the paint event.

            Args:
                browser: The browser instance.
                element_type: The type of element being painted.
                paint_buffer: The paint buffer.

            Raises:
                Exception: If the element type is unsupported.
            """
            if not self.OnPaint_called:
                self.OnPaint_called = True
            if element_type == cef.PET_VIEW:
                buffer_string = paint_buffer.GetBytes(mode="rgba", origin="top-left")
                browser.SetUserData("OnPaint.buffer_string", buffer_string)
            else:
                raise Exception("Unsupported element_type in OnPaint")

    try:
        sys.excepthook = cef.ExceptHook
        cef.Initialize(settings={"windowless_rendering_enabled": True})
        create_browser(url)
        cef.MessageLoop()
    finally:
        cef.Shutdown()


if __name__ == "__main__":
    get_screenshot(
        "https://github.com/cztomczak/cefpython", (0, 0, 800, 600), "test.png"
    )
