"""Additional tests for :mod:`pytigon_lib.schtools.images` beyond images_test.py."""

import io

import numpy as np
import pytest
from PIL import Image

from pytigon_lib.schtools.images import compare_images, mse, spec_resize, svg_to_png


class TestSpecResizeExtra:
    def test_resize_with_only_width(self):
        img = Image.new("RGB", (300, 300), color="green")
        result = spec_resize(img, width=600, height=0)
        assert result.size[0] == 600

    def test_resize_with_only_height(self):
        img = Image.new("RGB", (300, 300), color="blue")
        result = spec_resize(img, width=0, height=600)
        assert result.size[1] == 600

    def test_resize_no_change(self):
        img = Image.new("RGB", (300, 300), color="yellow")
        result = spec_resize(img, width=300, height=300)
        assert result.size == (300, 300)

    def test_resize_very_small_image(self):
        img = Image.new("RGB", (9, 9), color="red")
        result = spec_resize(img, width=27, height=27)
        assert result.size == (27, 27)

    def test_resize_raises_value_error(self):
        with pytest.raises(ValueError, match="Error during image resizing"):
            spec_resize(None, width=100, height=100)


class TestSvgToPngExtra:
    def test_svg_to_png_simple_min_scaling(self):
        svg_str = b'<svg width="100" height="100"><rect width="100" height="100" fill="red"/></svg>'
        png_bytes = svg_to_png(svg_str, 200, 50, "simple_min")
        assert isinstance(png_bytes, bytes)

    def test_svg_to_png_frame_no_dimensions(self):
        svg_str = b'<svg width="100" height="100"><rect width="100" height="100" fill="green"/></svg>'
        png_bytes = svg_to_png(svg_str, 0, 0, "frame")
        assert isinstance(png_bytes, bytes)

    def test_svg_to_png_frame_only_width(self):
        svg_str = b'<svg width="100" height="50"><rect width="100" height="50" fill="blue"/></svg>'
        png_bytes = svg_to_png(svg_str, width=200, height=0, image_type="frame")
        assert isinstance(png_bytes, bytes)

    def test_svg_to_png_frame_only_height(self):
        svg_str = b'<svg width="100" height="50"><rect width="100" height="50" fill="purple"/></svg>'
        png_bytes = svg_to_png(svg_str, width=0, height=100, image_type="frame")
        assert isinstance(png_bytes, bytes)

    def test_svg_to_png_simple_no_dimensions(self):
        svg_str = b'<svg width="100" height="100"><rect width="100" height="100" fill="orange"/></svg>'
        png_bytes = svg_to_png(svg_str, 0, 0, "simple")
        assert isinstance(png_bytes, bytes)

    def test_svg_to_png_simple_min_no_scaling(self):
        svg_str = b'<svg width="100" height="100"><rect width="100" height="100" fill="pink"/></svg>'
        png_bytes = svg_to_png(svg_str, 0, 0, "simple_min")
        assert isinstance(png_bytes, bytes)

    def test_svg_to_png_invalid_svg_raises(self):
        with pytest.raises(ValueError, match="Error during SVG to PNG conversion"):
            svg_to_png(b"not valid svg", 100, 100, "simple")


class TestMse:
    def test_mse_identical_images(self):
        arr = np.zeros((10, 10, 3), dtype=np.uint8)
        result = mse(arr, arr)
        assert result == 0.0

    def test_mse_different_images(self):
        arr1 = np.zeros((10, 10, 3), dtype=np.uint8)
        arr2 = np.ones((10, 10, 3), dtype=np.uint8) * 255
        result = mse(arr1, arr2)
        assert result > 0.0

    def test_mse_single_channel(self):
        arr1 = np.zeros((10, 10), dtype=np.uint8)
        arr2 = np.ones((10, 10), dtype=np.uint8) * 128
        result = mse(arr1, arr2)
        assert result > 0.0
        assert result == pytest.approx(16384.0, rel=1e-2)


class TestCompareImages:
    def test_compare_identical_images(self):
        img = Image.new("RGB", (100, 100), color="red")
        result = compare_images(img, img)
        assert result == 0.0

    def test_compare_different_size_images(self):
        img1 = Image.new("RGB", (100, 100), color="red")
        img2 = Image.new("RGB", (200, 200), color="red")
        result = compare_images(img1, img2)
        assert result == 0.0

    def test_compare_rgba_images(self):
        img1 = Image.new("RGBA", (50, 50), color=(255, 0, 0, 128))
        img2 = Image.new("RGBA", (50, 50), color=(255, 0, 0, 255))
        result = compare_images(img1, img2)
        assert result == 0.0

    def test_compare_different_colors(self):
        img1 = Image.new("RGB", (100, 100), color="blue")
        img2 = Image.new("RGB", (100, 100), color="red")
        result = compare_images(img1, img2)
        assert result > 0.0
