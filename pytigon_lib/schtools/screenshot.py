"""Headless screenshot capture using CEF Python (cefpython3).

Based on the cefpython example: screenshot.py

Requires cefpython3 and PIL (Pillow) to be installed.
"""

import sys

cef = None
try:
    from cefpython3 import cefpython as cef
except ImportError:
    pass

# Lazy-loaded PIL Image module
_IMAGE_MODULE = None


def _get_image():
    """Return the PIL Image module, loading it on first call."""
    global _IMAGE_MODULE
    if _IMAGE_MODULE is None:
        from PIL import Image as _IMAGE_MODULE
    return _IMAGE_MODULE


def get_screenshot(url, size, img_path):
    """Capture a screenshot of a web page in headless mode.

    Uses CEF (Chromium Embedded Framework) with windowless rendering
    to load the URL and capture the rendered content as a PNG image.

    Args:
        url: The URL to capture.
        size: A tuple of (x, y, width, height) for the viewport.
        img_path: File path where the PNG screenshot will be saved.

    Raises:
        RuntimeError: If cefpython3 is not installed.
        Exception: If the screenshot capture fails.
    """
    if cef is None:
        raise RuntimeError(
            "cefpython3 is required for screenshot capture. "
            "Install it with: pip install cefpython3"
        )

    def _create_browser():
        """Create an off-screen browser and attach handlers."""
        parent_window_handle = 0
        window_info = cef.WindowInfo()
        window_info.SetAsOffscreen(parent_window_handle)
        browser = cef.CreateBrowserSync(window_info=window_info, url=url)
        browser.SetClientHandler(LoadHandler(size, img_path))
        browser.SetClientHandler(RenderHandler(size))
        browser.SendFocusEvent(True)
        browser.WasResized()

    try:
        sys.excepthook = cef.ExceptHook
        cef.Initialize(settings={"windowless_rendering_enabled": True})
        _create_browser()
        cef.MessageLoop()
    finally:
        cef.Shutdown()


class LoadHandler:
    """CEF load handler: saves screenshot on load complete, exits on error."""

    def __init__(self, size, img_path):
        self.size = size
        self.img_path = img_path

    def OnLoadingStateChange(self, browser, is_loading, **_):
        """Triggered when the page loading state changes."""
        if not is_loading:
            _save_screenshot(browser, self.size, self.img_path)
            cef.PostTask(cef.TID_UI, _exit_app, browser)

    def OnLoadError(self, browser, frame, error_code, failed_url, **_):
        """Triggered on page load error."""
        if not frame.IsMain():
            return
        cef.PostTask(cef.TID_UI, _exit_app, browser)


class RenderHandler:
    """CEF render handler: provides view rect and captures paint buffer."""

    def __init__(self, size):
        self.size = size
        self.OnPaint_called = False

    def GetViewRect(self, rect_out, **_):
        """Return the view rectangle for off-screen rendering."""
        rect_out.extend((self.size[0], self.size[1], self.size[2], self.size[3]))
        return True

    def OnPaint(self, browser, element_type, paint_buffer, **_):
        """Capture the paint buffer on first paint."""
        if not self.OnPaint_called:
            self.OnPaint_called = True
        if element_type == cef.PET_VIEW:
            buffer_string = paint_buffer.GetBytes(mode="rgba", origin="top-left")
            browser.SetUserData("OnPaint.buffer_string", buffer_string)
        else:
            raise RuntimeError("Unsupported element_type in OnPaint")


def _save_screenshot(browser, size, path):
    """Convert the CEF paint buffer to a PNG and save to disk.

    Args:
        browser: The CEF browser instance.
        size: Viewport (x, y, width, height) tuple.
        path: Output file path.

    Raises:
        RuntimeError: If no paint buffer was captured.
    """
    buffer_string = browser.GetUserData("OnPaint.buffer_string")
    if not buffer_string:
        raise RuntimeError(
            "buffer_string is empty - OnPaint was never called or no content rendered"
        )
    Image = _get_image()
    image = Image.frombytes(
        "RGBA", (size[2], size[3]), buffer_string, "raw", "RGBA", 0, 1
    )
    image.save(path, "PNG")


def _exit_app(browser):
    """Close the browser and quit the CEF message loop."""
    browser.CloseBrowser()
    cef.QuitMessageLoop()


if __name__ == "__main__":
    get_screenshot(
        "https://github.com/cztomczak/cefpython", (0, 0, 800, 600), "test.png"
    )
