import io
from PIL import Image


def spec_resize(image, width=0, height=0):
    w = int(image.width / 3)
    h = int(image.height / 3)
    xtab = ((0, w), (w, image.width - w), (image.width - w, image.width))
    ytab = ((0, h), (h, image.height - h), (image.height - h, image.height))
    tab = []
    i = 0
    for y in ytab:
        for x in xtab:
            image2 = image.crop((x[0], y[0], x[1], y[1]))
            if True:
                if i in (0, 2, 6, 8):
                    pass
                elif i in (1, 7):
                    if width - 2 * w > 1:
                        image2 = image2.resize((width - 2 * w, h))
                    else:
                        image2 = image2.resize((1, h))
                elif i in (3, 5):
                    if height - 2 * h > 1:
                        image2 = image2.resize((w, height - 2 * h))
                    else:
                        image2 = image2.resize((w, 1))
                else:
                    if width - 2 * w > 0:
                        w2 = width - 2 * w
                    else:
                        w2 = 1
                    if height - 2 * h > 0:
                        h2 = height - 2 * h
                    else:
                        h2 = 1
                    image2 = image2.resize((w2, h2))
            tab.append(image2)
            i += 1

    xtab = (0, w, width - w)
    ytab = (0, h, height - h)
    dst = Image.new("RGB", (width, height))
    i = 0
    for y in ytab:
        for x in xtab:
            dst.paste(tab[i], (x, y))
            i += 1
    return dst


# image_type: "simple", "simple_min" or "frame"
def svg_to_png(svg_str, width=0, height=0, image_type="simple"):
    from svglib.svglib import svg2rlg
    from reportlab.graphics import renderPM

    svg_io = io.BytesIO(svg_str)
    drawing = svg2rlg(svg_io)

    if image_type in ("simple", "simple_min"):
        scale_x = 0
        scale_y = 0

        if width > 0:
            scale_x = width / drawing.width
        if height > 0:
            scale_y = height / drawing.height
        if not scale_y and scale_x:
            scale_y = scale_x
        elif not scale_x and scale_y:
            scale_x = scale_y
        elif not scale_x and not scale_y:
            scale_x = scale_y = 1

        if image_type == "simple_min":
            if scale_x and scale_x < scale_y:
                scale_y = scale_x
            elif scale_y:
                scale_x = scale_y

        drawing.width *= scale_x
        drawing.height *= scale_y
        drawing.scale(scale_x, scale_y)

        return drawing.asString("png")
    else:
        if width or height:
            if not height:
                height = int(drawing.height * width / drawing.width)
            if not width:
                width = int(drawing.width * height / drawing.height)
            img = Image.open(io.BytesIO(drawing.asString("png")))
            img2 = spec_resize(img, width, height)
            output = io.BytesIO()
            img2.save(output, "PNG")
            img2_bytes = output.getvalue()
            return img2_bytes
        else:
            return drawing.asString("png")
