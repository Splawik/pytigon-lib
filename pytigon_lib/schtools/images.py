import io
from PIL import Image
from svglib.svglib import svg2rlg
from reportlab.graphics import renderPM


def spec_resize(image, width=0, height=0):
    """
    Resize the image by dividing it into 9 parts and resizing each part accordingly.

    Args:
        image (PIL.Image): The image to resize.
        width (int): The desired width of the output image.
        height (int): The desired height of the output image.

    Returns:
        PIL.Image: The resized image.
    """
    try:
        w = int(image.width / 3)
        h = int(image.height / 3)

        # Define the x and y coordinates for cropping
        xtab = ((0, w), (w, image.width - w), (image.width - w, image.width))
        ytab = ((0, h), (h, image.height - h), (image.height - h, image.height))

        tab = []
        i = 0

        # Crop and resize each part of the image
        for y in ytab:
            for x in xtab:
                image2 = image.crop((x[0], y[0], x[1], y[1]))

                if i in (1, 7):  # Top and bottom middle parts
                    new_width = max(1, width - 2 * w)
                    image2 = image2.resize((new_width, h))
                elif i in (3, 5):  # Left and right middle parts
                    new_height = max(1, height - 2 * h)
                    image2 = image2.resize((w, new_height))
                elif i == 4:  # Center part
                    new_width = max(1, width - 2 * w)
                    new_height = max(1, height - 2 * h)
                    image2 = image2.resize((new_width, new_height))

                tab.append(image2)
                i += 1

        # Define the x and y coordinates for pasting
        xtab = (0, w, width - w)
        ytab = (0, h, height - h)

        # Create a new image and paste the resized parts
        dst = Image.new("RGB", (width, height))
        i = 0
        for y in ytab:
            for x in xtab:
                dst.paste(tab[i], (x, y))
                i += 1

        return dst

    except Exception as e:
        raise ValueError(f"Error during image resizing: {e}")


def svg_to_png(svg_str, width=0, height=0, image_type="simple"):
    """
    Convert an SVG string to a PNG image with optional resizing.

    Args:
        svg_str (bytes): The SVG string to convert.
        width (int): The desired width of the output image.
        height (int): The desired height of the output image.
        image_type (str): The type of image to generate ("simple", "simple_min", or "frame").

    Returns:
        bytes: The PNG image as bytes.
    """
    try:
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

                img = Image.open(io.BytesIO(drawing.asString("png")))
                img2 = spec_resize(img, width, height)

                output = io.BytesIO()
                img2.save(output, "PNG")
                return output.getvalue()

            else:
                return drawing.asString("png")

    except Exception as e:
        raise ValueError(f"Error during SVG to PNG conversion: {e}")
