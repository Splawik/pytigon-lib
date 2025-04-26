from pytigon_lib.schtools.images import *
from PIL import Image

# Pytest tests
import pytest


def test_spec_resize():
    img = Image.new("RGB", (300, 300), color="red")
    resized_img = spec_resize(img, 600, 600)
    assert resized_img.size == (600, 600)


def test_svg_to_png_simple():
    svg_str = b'<svg width="100" height="100"><rect width="100" height="100" fill="red"/></svg>'
    png_bytes = svg_to_png(svg_str, 200, 200, "simple")
    assert isinstance(png_bytes, bytes)


def test_svg_to_png_frame():
    svg_str = b'<svg width="100" height="100"><rect width="100" height="100" fill="blue"/></svg>'
    png_bytes = svg_to_png(svg_str, 200, 200, "frame")
    assert isinstance(png_bytes, bytes)


if __name__ == "__main__":
    pytest.main()
