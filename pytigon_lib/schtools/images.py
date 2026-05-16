"""Image processing utilities: 9-slice resizing, SVG-to-PNG conversion, image comparison."""

import io

# Lazy-loaded module references (imported on first use to avoid
# heavy dependencies when image functionality is not needed).
_IMAGE_MODULE = None
_NP_MODULE = None
_SVGLIB_MODULE = None


def _get_image():
    """Lazy-load and return the PIL Image module."""
    global _IMAGE_MODULE
    if _IMAGE_MODULE is None:
        from PIL import Image as _IMAGE_MODULE
    return _IMAGE_MODULE


def _get_np():
    """Lazy-load and return the numpy module."""
    global _NP_MODULE
    if _NP_MODULE is None:
        import numpy as _NP_MODULE
    return _NP_MODULE


def _get_svg2rlg():
    """Lazy-load and return the svglib svg2rlg function."""
    global _SVGLIB_MODULE
    if _SVGLIB_MODULE is None:
        from svglib.svglib import svg2rlg as _SVGLIB_MODULE
    return _SVGLIB_MODULE


def spec_resize(image, width=0, height=0):
    """Resize an image using 9-slice scaling (scale-9 grid).

    Divides the image into a 3x3 grid and resizes the centre/edge cells
    independently while keeping corner cells at their original size.
    This preserves border/corner details while allowing the overall
    dimensions to change.

    Args:
        image: A PIL Image object.
        width: Desired output width in pixels.
        height: Desired output height in pixels.

    Returns:
        A new PIL Image resized to (width, height).

    Raises:
        ValueError: If resize fails due to invalid dimensions or image data.
    """
    try:
        w = int(image.width / 3)
        h = int(image.height / 3)

        # Crop regions: (left, upper, right, lower)
        xtab = ((0, w), (w, image.width - w), (image.width - w, image.width))
        ytab = ((0, h), (h, image.height - h), (image.height - h, image.height))

        tab = []
        i = 0
        Image = _get_image()

        for y in ytab:
            for x in xtab:
                image2 = image.crop((x[0], y[0], x[1], y[1]))

                if i in (1, 7):  # Top-middle and bottom-middle
                    new_width = max(1, width - 2 * w)
                    image2 = image2.resize((new_width, h))
                elif i in (3, 5):  # Middle-left and middle-right
                    new_height = max(1, height - 2 * h)
                    image2 = image2.resize((w, new_height))
                elif i == 4:  # Centre
                    new_width = max(1, width - 2 * w)
                    new_height = max(1, height - 2 * h)
                    image2 = image2.resize((new_width, new_height))

                tab.append(image2)
                i += 1

        # Paste positions for the 3x3 grid
        xtab_paste = (0, w, width - w)
        ytab_paste = (0, h, height - h)

        dst = Image.new("RGB", (width, height))
        i = 0
        for y in ytab_paste:
            for x in xtab_paste:
                dst.paste(tab[i], (x, y))
                i += 1

        return dst

    except Exception as e:
        raise ValueError(f"Error during image resizing: {e}")


def svg_to_png(svg_str, width=0, height=0, image_type="simple"):
    """Convert an SVG string to a PNG image.

    Supports three rendering modes:
    - ``simple``: Scale proportionally to fit width or height.
    - ``simple_min``: Scale uniformly to fit within bounds.
    - ``frame``: Use 9-slice scaling (see :func:`spec_resize`).

    Args:
        svg_str: SVG content as bytes.
        width: Desired output width (0 = use natural width).
        height: Desired output height (0 = use natural height).
        image_type: Rendering mode: 'simple', 'simple_min', or 'frame'.

    Returns:
        PNG image data as bytes.

    Raises:
        ValueError: If conversion fails.
    """
    try:
        svg2rlg = _get_svg2rlg()
        svg_io = io.BytesIO(svg_str)
        drawing = svg2rlg(svg_io)

        if image_type in ("simple", "simple_min"):
            scale_x = scale_y = 1

            if width > 0:
                scale_x = width / drawing.width
            if height > 0:
                scale_y = height / drawing.height

            if image_type == "simple_min":
                scale_x = scale_y = min(scale_x, scale_y)
            else:
                if not scale_y and scale_x:
                    scale_y = scale_x
                elif not scale_x and scale_y:
                    scale_x = scale_y

            drawing.width *= scale_x
            drawing.height *= scale_y
            drawing.scale(scale_x, scale_y)

            return drawing.asString("png")

        else:  # image_type == "frame"
            if width or height:
                if not height:
                    height = int(drawing.height * width / drawing.width)
                if not width:
                    width = int(drawing.width * height / drawing.height)

                Image = _get_image()
                img = Image.open(io.BytesIO(drawing.asString("png")))
                img2 = spec_resize(img, width, height)

                output = io.BytesIO()
                img2.save(output, "PNG")
                return output.getvalue()

            else:
                return drawing.asString("png")

    except Exception as e:
        raise ValueError(f"Error during SVG to PNG conversion: {e}")


def mse(image_array1, image_array2):
    """Compute the Mean Squared Error (MSE) between two image arrays.

    Args:
        image_array1: First image as a numpy ndarray.
        image_array2: Second image as a numpy ndarray.

    Returns:
        The MSE value as a float (lower = more similar).
    """
    np = _get_np()
    err = np.sum((image_array1.astype("float") - image_array2.astype("float")) ** 2)
    err /= float(image_array1.shape[0] * image_array1.shape[1])
    return err


def compare_images(img1, img2):
    """Compare two images and return their Mean Squared Error.

    The second image is resized to match the first image's dimensions
    before comparison.

    Args:
        img1: Reference PIL Image.
        img2: PIL Image to compare against the reference.

    Returns:
        The MSE value (float). Lower values indicate greater similarity.
    """
    np = _get_np()
    Image = _get_image()

    img2_mod = img2.convert("RGB").resize(
        (img1.size[0], img1.size[1]), Image.Resampling.LANCZOS
    )
    return mse(np.array(img1.convert("RGB")), np.array(img2_mod))
