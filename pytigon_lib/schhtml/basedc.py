"""
This module provides classes and functions for managing device contexts (DC) and sub-device contexts (SubDc) for drawing operations. It includes the following classes:

- BaseDc: Represents a base device context with methods for drawing shapes, text, and images, as well as managing document state and pages.
- BaseDcInfo: Provides information and utility methods for the BaseDc class, such as text measurements and style management.
- SubDc: Represents a sub-device context that inherits properties and methods from a parent device context.
- NullDc: A null device context that performs no actual drawing but tracks the maximum dimensions of the content.
- NullDcinfo: Provides information and utility methods for the NullDc class.

The module also includes a decorator function `convert_fun_arg` that modifies the positional and keyword arguments of a function to adjust coordinates and dimensions based on the object's attributes.

Classes:
    BaseDc: Represents a base device context with methods for drawing shapes, text, and images, as well as managing document state and pages.
    BaseDcInfo: Provides information and utility methods for the BaseDc class, such as text measurements and style management.
    SubDc: Represents a sub-device context that inherits properties and methods from a parent device context.
    NullDc: A null device context that performs no actual drawing but tracks the maximum dimensions of the content.
    NullDcinfo: Provides information and utility methods for the NullDc class.

Functions:
    convert_fun_arg(fn): A decorator that modifies the positional and keyword arguments of a function to adjust coordinates and dimensions based on the object's attributes.
"""

import zipfile
import io

from pytigon_lib.schtools.schjson import json_loads, json_dumps


class BaseDc(object):
    def __init__(
        self,
        calc_only=False,
        width=None,
        height=None,
        output_name=None,
        output_stream=None,
        scale=1.0,
        notify_callback=None,
        record=False,
    ):
        """
        :param calc_only: If True, no output will be generated
        :param width: Width of the document in points
        :param height: Height of the document in points
        :param output_name: Name of the output file
        :param output_stream: Output stream
        :param scale: Scale factor
        :param notify_callback: Callback function with two arguments: event name and dictionary
        :param record: If True, all operations will be recorded in self.store
        """
        self.x = 0
        self.y = 0
        self.gparent = None
        self.dc_info = BaseDcInfo(self)

        self.store = []
        self.rec = record
        self.calc_only = calc_only

        self.default_width = int(210 * 72 / 25.4)
        self.default_height = int(297 * 72 / 25.4)
        if width == None:
            self.width = self.default_width
        else:
            self.width = width
        if height == None:
            self.height = self.default_height
        else:
            self.height = height
        self.output_name = output_name
        self.output_stream = output_stream
        self.base_font_size = 10
        self.paging = False
        self.pages = []
        self._maxwidth = 0
        self._maxheight = 0
        self.last_style = "None"
        self.scale = scale
        self.notify_callback = notify_callback
        self.handle_html_directly = False

    @property
    def dx(self):
        """
        Width of the document in points
        """
        return self.width

    @property
    def dy(self):
        """
        Height of the document in points
        """
        return self.height

    def close(self):
        """
        Closes the document.

        This method is called when the document is being
        finalised. It is called automatically, but you can call
        it manually if you want to make sure all the resources
        are released.
        """
        pass

    def state(self):
        """
        Returns a list representing the state of the document.

        The list contains the following items:
        - The number of pages
        - The width of the document in points
        - The height of the document in points
        - The base font size
        - True or False whether the document is paged or not
        - The maximum width of the content
        - The maximum height of the content
        - The list of styles used in the document
        - The last style used in the document
        """
        rec = [
            len(self.pages),
            self.width,
            self.height,
            self.base_font_size,
            self.paging,
            self._maxwidth,
            self._maxheight,
        ]
        if self.dc_info:
            rec.append(self.dc_info.styles)
        else:
            rec.append([])
        rec.append(self.last_style)
        return rec

    def set_scale(self, scale):
        """
        Set the scale of the document.

        Args:
            scale (float): The scale factor.
        """
        self.scale = scale

    def restore_state(self, state):
        """
        Restores the state of the document from a given state list.

        Args:
            state (list): A list containing the state information of the document,
                        which includes:
                        - Index 1: The width of the document in points
                        - Index 2: The height of the document in points
                        - Index 3: The base font size
                        - Index 4: Boolean indicating whether the document is paged
                        - Index 5: The maximum width of the content
                        - Index 6: The maximum height of the content
                        - Index 7: The list of styles used in the document (if applicable)
                        - Index 8: The last style used in the document
        """
        self.width = state[1]
        self.height = state[2]
        self.base_font_size = state[3]
        self.paging = state[4]
        self._maxwidth = state[5]
        self._maxheight = state[6]
        if self.dc_info:
            self.dc_info.styles = state[7]
        self.last_style = state[8]

    def get_max_sizes(self):
        """
        Returns the maximum width and height of the document content in points.

        :rtype: tuple
        :return: A tuple (width, height) containing the maximum width and height of the document content in points.
        """
        return (self._maxwidth, self._maxheight)

    def test_point(self, x, y):
        """
        Tests if a point is within the document's maximum size.

        :param x: The x-coordinate of the point
        :param y: The y-coordinate of the point
        :return: None
        """
        if x > self._maxwidth:
            self._maxwidth = x
        if y > self._maxheight:
            self._maxheight = y

    def set_paging(self, enable=True):
        """
        Enables or disables paging.

        :param enable: Boolean indicating whether to enable or disable paging
        :return: None
        """
        self.paging = enable

    def get_page_count(self):
        """
        Returns the number of pages in the document.

        :rtype: int
        :return: The number of pages in the document
        """
        return len(self.pages)

    def set_base_font_size(self, size):
        """
        Sets the base font size for the document.

        :param size: The base font size
        :type size: int
        :return: None
        """
        self.base_font_size = size

    def is_calc_only(self):
        """
        Checks if the document is in calculation-only mode.

        :return: boolean indicating whether the document is in calculation-only mode
        """
        return self.calc_only

    def get_size(self):
        """
        Returns the size of the document as a list containing the width and height in points.

        :rtype: list
        :return: A list with two elements: [width, height]
        """
        return [self.width, self.height]

    def rgbfromhex(self, hex):
        """
        Converts a hex color code to a tuple of RGB values.

        :param hex: hex color code, e.g. #000000 or #ffffff
        :type hex: str
        :return: tuple of RGB values
        :rtype: tuple
        """
        if len(hex) == 4:  #  #000
            (r, g, b) = (hex[1], hex[2], hex[3])
            (r, g, b) = [int(n, 16) * 16 for n in (r, g, b)]
        elif len(hex) == 7:  # #00ff00
            (r, g, b) = (hex[1:3], hex[3:5], hex[5:])
            (r, g, b) = [int(n, 16) for n in (r, g, b)]
        else:
            r = 0
            g = 0
            b = 0
        return (r, g, b)

    def subdc(
        self,
        x,
        y,
        dx,
        dy,
        reg_max=True,
    ):
        """
        Creates a sub-device context (SubDc) for the current device context.

        :param x: The x-coordinate of the top left corner of the sub-device context
        :type x: int
        :param y: The y-coordinate of the top left corner of the sub-device context
        :type y: int
        :param dx: The width of the sub-device context
        :type dx: int
        :param dy: The height of the sub-device context
        :type dy: int
        :param reg_max: If True (default), the sub-device context will automatically
            update the maximum width and height of the device context
        :type reg_max: bool
        :return: The created sub-device context
        :rtype: SubDc
        """

        return SubDc(self, x, y, dx, dy, reg_max)

    def get_dc_info(self):
        """
        Returns the device context information for the current device context.

        :return: the device context information
        :rtype: BaseDcInfo
        """
        return self.dc_info

    def record(self, name, args=None):
        """
        Records an action in the device context's action log.

        :param name: The name of the action to record
        :type name: str
        :param args: The arguments to the action, if any
        :type args: list or None
        """
        if self.rec:
            self.store.append((name, args))

    def play(self, page=-1):
        """
        Replays the actions in the device context's action log.

        :param page: The page to play back. If -1, all pages are played back.
        :type page: int
        :return: None
        """
        rec = self.rec
        self.rec = False
        if page >= 0:
            # self.store = self.pages[page]
            pages = [
                self.pages[page],
            ]
        else:
            pages = self.pages
        first = True
        for store in pages:
            if first:
                first = False
            else:
                self.start_page()
            for pos in store:
                fun = getattr(self, pos[0])
                if pos[1]:
                    fun(*pos[1])
                else:
                    fun()
            self.end_page()
        self.rec = rec

    def play_str(self, str):
        """
        Replays a string of actions in the device context.

        The string is expected to be a newline-separated list of JSON-encoded
        actions. Each action is a list of two items: the first is the name of the
        method to call, and the second is a list of arguments to that method (or
        None if there are no arguments).

        :param str: The string of actions to replay
        :type str: str
        :return: None
        """
        for buf in str.split("\n"):
            buf = buf.strip()
            if buf != "":
                pos = json_loads(buf)
                fun = getattr(self, pos[0])
                if pos[1]:
                    fun(*pos[1])
                else:
                    fun()

    def save(self, zip_name):
        """
        Saves the device context to a ZIP file.

        The ZIP file will contain a single file 'set.dat' which is a JSON-encoded
        representation of the state of the document (see :meth:`state` for details),
        and multiple files 'page_1', 'page_2', etc, each of which is a JSON-encoded
        representation of the actions on that page.

        :param zip_name: The name of the file to save to
        :type zip_name: str
        :return: None
        """
        try:
            zf = zipfile.ZipFile(zip_name, mode="w", compression=zipfile.ZIP_BZIP2)
        except:
            zf = zipfile.ZipFile(
                zip_name, mode="w", compression=zipfile.ZIP_BZIP2ZIP_DEFLATED
            )

        zf.writestr("set.dat", json_dumps(self.state()))
        i = 1
        for page in self.pages:
            buf = io.BytesIO()
            for rec in page:
                # try:
                if True:
                    buf.write(json_dumps(rec).encode("utf-8"))
                # except:
                #    print("basedc:", rec.__class__, rec)
                buf.write(b"\n")
            zf.writestr("page_%d" % i, buf.getvalue())
            i += 1
        zf.close()

    def load(self, zip_name):
        """
        Loads the device context from a ZIP file.

        The ZIP file is expected to contain a 'set.dat' file, which holds a JSON-encoded
        representation of the document's state, and multiple files named 'page_1', 'page_2', etc.,
        each having a JSON-encoded representation of the actions on that page.

        :param zip_name: The name of the ZIP file to load from
        :type zip_name: str
        :return: None
        """
        zf = zipfile.ZipFile(zip_name, mode="r")
        parm = json_loads(zf.read("set.dat").decode("utf-8"))
        count = parm[0]
        self.pages = []
        self.width = parm[1]
        self.height = parm[2]
        self.base_font_size = parm[3]
        self.paging = parm[4]
        self._maxwidth = parm[5]
        self._maxheight = parm[6]
        if self.dc_info:
            self.dc_info.styles = parm[7]
        for i in range(1, count + 1):
            rec = []
            data = zf.read("page_%d" % i).decode("utf-8")
            for line in data.split("\n"):
                if len(line) > 1:
                    buf = json_loads(line)
                    rec.append(buf)
            self.pages.append(rec)
            # self.rec = rec
        zf.close()

    def _scale_image(self, x, y, dx, dy, scale, image_w, image_h):
        """
        Calculates scaling factors for an image based on the given dimensions and scale type.

        This function determines the scaling factors for the x and y axes based on the
        target dimensions (dx, dy), the original image dimensions (image_w, image_h),
        and a specified scale type. The scale type dictates how the aspect ratio should
        be preserved or modified.

        :param x: Not used in the calculation.
        :param y: Not used in the calculation.
        :param dx: Target width for scaling.
        :param dy: Target height for scaling.
        :param scale: The type of scaling to apply:
                    - 0: No scaling, keep original size.
                    - 1: Scale to fit both dimensions, preserving aspect ratio.
                    - 2: Scale to fit the larger dimension, preserving aspect ratio.
                    - 3: Scale to fit the smaller dimension, preserving aspect ratio.
                    - 4 or above: No scaling, keep original size.
        :param image_w: Original image width.
        :param image_h: Original image height.
        :return: A tuple (x_scale, y_scale) representing the scaling factors for the x and y axes.
        """

        if scale < 4:
            x_scale = 1
            y_scale = 1
            if scale > 0:
                if dx > 0:
                    x_scale = dx / image_w
                    if dy > 0:
                        y_scale = dy / image_h
                    else:
                        y_scale = x_scale
                else:
                    if dy > 0:
                        y_scale = dy / image_h
                        x_scale = y_scale
                    else:
                        x_scale = 1
                        y_scale = 1
                if scale == 2:
                    if x_scale < y_scale:
                        x_scale = y_scale
                    else:
                        y_scale = x_scale
                if scale == 3:
                    if x_scale < y_scale:
                        y_scale = x_scale
                    else:
                        x_scale = y_scale
        else:
            x_scale = 1
            y_scale = 1
        return (x_scale, y_scale)

    def end_document(self):
        """
        Ends the document, finalising the page list.

        This method must be called after all drawing operations have been completed.
        It ensures that the page list is complete and ready for saving or other
        operations.

        :return: None
        """
        if len(self.store) > 0:
            self.pages.append(self.store)

    def start_page(self):
        """
        Starts a new page in the document.

        This method should be called before starting to draw on a new page.
        It ensures that the current page is completed and stored in the page list.
        It also resets the current style.

        :return: None
        """
        if len(self.store) > 0:
            self.pages.append(self.store)
            self.store = []
        self.last_style = "None"
        if self.notify_callback:
            self.notify_callback("start_page", {"dc": self})

    def end_page(self):
        """
        Ends the current page in the document.

        This method should be called after completing drawing on a page.
        It ensures that the current page is finalized and added to the page list.
        After calling this method, a new page can be started using `start_page`.

        :return: None
        """
        if self.notify_callback:
            self.notify_callback("end_page", {"dc": self})
        if len(self.store) > 0:
            self.pages.append(self.store)
            self.store = []
        self.last_style = "None"

    def fill(self, *args):
        """
        Fills a shape or area with the current fill settings.

        :param args: Parameters specifying the shape or area to fill
        :return: None
        """
        self.record("fill", args)

    def draw(self, *args):
        """
        Draws a shape or line on the document.

        :param args: Parameters specifying the shape or line to draw
        :return: None
        """
        self.record("draw", args)

    def set_color(self, *args):
        """
        Sets the color for subsequent drawing operations.

        This method records the color setting operation with the provided
        arguments, which specify the color to be used.

        :param args: Color parameters, which could include RGB values,
                    hexadecimal color codes, or any other color representation.
        :return: None
        """
        self.record("set_color", args)

    def set_line_width(self, *args):
        """
        Sets the line width for subsequent drawing operations.

        This method records the line width setting operation with the provided
        arguments, which specify the width of the line to be used.

        :param args: Line width parameters, which could include a single integer
                    value or a list of values.
        :return: None
        """
        self.record("set_line_width", args)

    def set_style(self, *args):
        """
        Sets the style for subsequent drawing operations.

        This method records the style setting operation with the provided
        arguments, which specify the style to be used.

        :param args: Style parameters, which could include a style name or a list
                    of style parameters.
        :return: None
        """
        self.last_style = args[0]
        self.record("set_style", args)

    def add_line(self, *args):
        """
        Adds a line to the document.

        This method records the line addition operation with the provided
        arguments, which specify the line to be added.

        :param args: Line parameters, which could include two points (x1, y1, x2, y2)
                    or four coordinates (x1, y1, x2, y2).
        :return: None
        """
        self.record("add_line", args)

    def add_rectangle(self, *args):
        """
        Adds a rectangle to the document.

        This method records the rectangle addition operation with the provided
        arguments, which specify the rectangle to be added.

        :param args: Rectangle parameters, which could include coordinates
                     (x, y, width, height) or a list of such values.
        :return: None
        """

        self.record("add_rectangle", args)

    def add_rounded_rectangle(self, *args):
        """
        Adds a rounded rectangle to the document.

        This method records the rounded rectangle addition operation with the provided
        arguments, which specify the rounded rectangle to be added.

        :param args: Rounded rectangle parameters, which could include coordinates
                     (x, y, width, height, radius) or a list of such values.
        :return: None
        """
        self.record("add_rounded_rectangle", args)

    def add_arc(self, *args):
        """
        Adds an arc to the document.

        This method records the arc addition operation with the provided
        arguments, which specify the arc to be added.

        :param args: Arc parameters, which could include coordinates
                     (x, y, radius, angle1, angle2) or a list of such values.
        :return: None
        """

        self.record("add_arc", args)

    def add_ellipse(self, *args):
        """
        Adds an ellipse to the document.

        This method records the ellipse addition operation with the provided
        arguments, which specify the ellipse to be added.

        :param args: Ellipse parameters, which could include coordinates
                    (x, y, width, height) or a list of such values.
        :return: None
        """
        self.record("add_ellipse", args)

    def add_polygon(self, *args):
        """
        Adds a polygon to the document.

        This method records the polygon addition operation with the provided
        arguments, which specify the polygon to be added.

        :param args: Polygon parameters, which could include coordinates
                     (x1, y1, x2, y2, ...) or a list of such values.
        :return: None
        """
        self.record("add_polygon", args)

    def add_spline(self, *args):
        """
        Adds a spline to the document.

        This method records the spline addition operation with the provided
        arguments, which specify the spline to be added.

        :param args: Spline parameters, which could include coordinates
                     (x1, y1, x2, y2, ...) or a list of such values.
        :return: None
        """
        self.record("add_spline", args)

    def draw_text(self, *args):
        """
        Draws text on the document.

        This method records the text drawing operation with the provided
        arguments, which specify the text to be drawn.

        :param args: Text parameters, which could include coordinates
                    (x, y) and a string of text.
        :return: None
        """
        self.record("draw_text", args)

    def draw_rotated_text(self, *args):
        """
        Draws rotated text on the document.

        This method records the rotated text drawing operation with the provided
        arguments, which specify the text to be drawn.

        :param args: Rotated text parameters, which could include coordinates
                    (x, y), a string of text, and the angle of rotation.
        :return: None
        """
        self.record("draw_rotated_text", args)

    def draw_image(self, *args):
        """
        Draws an image on the document.

        This method records the image drawing operation with the provided
        arguments, which specify the image to be drawn.

        :param args: Image parameters, which could include coordinates
                    (x, y), the width and height of the image, scale type,
                    and the image data.
        :return: None
        """
        self.record("draw_image", args)

    def draw_atom_line(self, x, y, line):
        """
        Draws a line of atoms.

        This method records the drawing operation of a line of atoms with the provided
        arguments, which specify the line of atoms to be drawn.

        :param x: The x-coordinate of the starting point of the line.
        :param y: The y-coordinate of the starting point of the line.
        :param line: A :class:`Line` instance representing the line of atoms to be drawn.
        :return: None
        """
        self.last_style = "None"
        dx = 0
        test = 0
        for obj in line.objs:
            if obj.style and obj.style >= 0:
                style = self.set_style(obj.style)
            else:
                style = self.set_style(0)
            if style[5] == "1":
                self.add_line(
                    (x + dx) - 1, y + line.dy_up + 2, obj.dx - obj.dx_space + 1, 0
                )
                self.draw()
            if type(obj.data) == str:
                ret = False
                if obj.parent and hasattr(obj.parent, "draw_atom"):
                    ret = obj.parent.draw_atom(
                        self,
                        obj.style,
                        x + dx,
                        (y + line.dy_up) - obj.dy_up,
                        obj.get_width(),
                        obj.get_height(),
                    )
                if not ret:
                    self.draw_text(x + dx, y + line.dy_up, obj.data.replace("»", " "))
            else:
                obj.data.draw_atom(
                    self,
                    obj.style,
                    x + dx,
                    (y + line.dy_up) - obj.dy_up,
                    obj.get_width(),
                    obj.get_height(),
                )
            dx += obj.dx

    def annotate(self, what, data):
        """
        Annotates the document with additional data.

        This method records an annotation for the document, which can be
        used to store additional information about the document.

        :param what: The type of annotation.
        :param data: The value of the annotation.
        :return: None
        """
        pass


class BaseDcInfo(object):
    def __init__(self, dc):
        """
        Initializes the BaseDcInfo instance.

        :param dc: The device context associated with this BaseDcInfo instance.
        :type dc: BaseDc
        """
        self.dc = dc
        self.styles = []

    def get_text_width(self, txt, style):
        """
        Calculates the width of the text in the given style.

        :param txt: The text to measure.
        :param style: The style to use for the measurement.
        :return: The width of the text in the given style.
        """

        return 12 * len(txt)

    def get_text_height(self, txt, style):
        """
        Calculates the height of the text in the given style.

        :param txt: The text to measure.
        :param style: The style to use for the measurement.
        :return: The height of the text in the given style.
        """
        return 12

    def get_line_dy(self, height):
        """
        Calculates the line spacing for the given line height.

        :param height: The line height.
        :return: The line spacing.
        """
        return height * 12

    def get_multiline_text_width(self, txt, style="default"):
        """
        Calculates the optimal, minimum, and maximum text widths for multiline text.

        This function splits the input text into individual words, calculates the width
        of each word, and determines the minimum and maximum widths. It also calculates
        an optimal width based on the total text width, limited by a factor of 16 if
        the number of words exceeds 16.

        :param txt: The input text to measure.
        :param style: The style to use for the measurement (default is "default").
        :return: A tuple (optsize, minsize, maxsize) representing the optimal, minimum,
                and maximum widths of the text.
        """
        txt_tab = txt.split(" ")
        minsize = 0
        for word in txt_tab:
            size = self.get_text_width(word, style)
            if size > minsize:
                minsize = size
        maxsize = self.get_text_width(txt, style)
        if len(txt_tab) > 16:
            optsize = (maxsize * 16) / len(txt_tab)
        else:
            optsize = maxsize
        return (optsize, minsize, maxsize)

    def get_multiline_text_height(self, txt, width, style="default"):
        """
        Calculates the height of the given multiline text and the text lines.

        This function splits the input text into individual words, checks if the width
        of each word exceeds the given width, and if so, adds the current line to the
        output list and resets the line to the current word. It also keeps track of the
        total height of the text.

        :param txt: The input text to measure.
        :param width: The width to check against.
        :param style: The style to use for the measurement (default is "default").
        :return: A tuple (height, lines) representing the height of the text and a list
                of the individual text lines.
        """
        lines = []
        line = ""
        line_ok = ""
        dy = 0
        txt_tab = txt.dc.split(" ")
        for pos in txt_tab:
            if line == "":
                line = pos
            else:
                line = line + " " + pos
            if self.get_text_width(line, style) > width:
                lines.append(line_ok)
                dy += self.get_text_height(line_ok, style)
                line = pos
                line_ok = pos
            else:
                line_ok = line
        if line_ok != "":
            lines.append(line_ok)
            dy += self.get_text_height(line_ok, style)
        return (dy, lines)

    def get_extents(self, word, style):
        """
        Calculates the text extents for a given word and style.

        This function calculates the width and height of a given word in a given
        style, as well as the width of a space in the same style. It also calculates
        the vertical offset for the top and bottom of the text.

        :param word: The word to calculate the text extents for.
        :param style: The style to use for the calculation.
        :return: A tuple (dx, dx_space, dy_up, dy_down) representing the width of the
                word, the width of a space, the vertical offset for the top of the
                text, and the vertical offset for the bottom of the text.
        """
        dx = self.get_text_width(word, style)
        dx_space = self.get_text_width(" ", style)
        dy = self.get_text_height(word, style)
        dy_up = dy / 2
        dy_down = dy - dy_up
        return (dx, dx_space, dy_up, dy_down)

    def get_style_id(self, style):
        """
        Returns an ID for the given style.

        The ID is a zero-based index into the list of styles. If the style is not
        already in the list, it will be added and the new ID will be returned.

        :param style: The style for which to return an ID.
        :return: The ID of the style.
        """
        i = 0
        for pos in self.styles:
            if style == pos:
                return i
            i += 1
        self.styles.append(style)
        return i


def convert_fun_arg(fn):
    """
    A decorator that modifies the positional and keyword arguments of a function.

    This decorator adjusts the x and y coordinates by adding the object's x and y
    attributes to them. It also updates the dx and dy dimensions based on the
    object's dimensions if they are provided as -1.

    The decorator handles both positional and keyword arguments, ensuring that
    the modified arguments are passed to the decorated function.

    :param fn: The function to be decorated.
    :return: The modified function with adjusted arguments.
    """

    def fun(self, *args, **kwargs):
        dx = 0
        dy = 0
        test = 0
        if len(args) > 1:
            dx = args[0]
            dy = args[1]
            arg1 = dx + self.x
            arg2 = dy + self.y
            test = 1
        else:
            if "x" in kwargs:
                dx = kwargs["x"]
                kwargs["x"] = dx + self.x
            if "y" in kwargs:
                dy = kwargs["y"]
                kwargs["y"] = dy + self.y
        if len(args) > 3:
            if args[2] == -1:
                arg3 = self.dx - dx
            else:
                arg3 = args[2]
            if args[3] == -1:
                arg4 = self.dy - dy
            else:
                arg4 = args[3]
            test = 2
        else:
            if "dx" in kwargs:
                if kwargs["dx"] == -1:
                    kwargs["dx"] = self.dx - dx
            if "dy" in kwargs:
                if kwargs["dx"] == -1:
                    kwargs["dx"] = self.dy - dy
        if test == 0:
            return fn(self, *args, **kwargs)
        if test == 1:
            return fn(self, *(arg1, arg2) + args[2:], **kwargs)
        if test == 2:
            return fn(self, *(arg1, arg2, arg3, arg4) + args[4:], **kwargs)

    return fun


class SubDc(object):
    def __init__(self, parent, x, y, dx, dy, reg_max=True):
        """
        Initializes a SubDc object.

        The SubDc object is a device context object that is a sub-device context
        of another device context. The sub-device context is defined by its
        top-left corner (x,y), width (dx) and height (dy) in points.

        The SubDc object is created by calling the subdc method of the parent
        device context.

        :param parent: The parent device context.
        :type parent: :class:`BaseDc` or :class:`SubDc`
        :param x: The x-coordinate of the top-left corner of the sub-device context.
        :type x: int
        :param y: The y-coordinate of the top-left corner of the sub-device context.
        :type y: int
        :param dx: The width of the sub-device context.
        :type dx: int
        :param dy: The height of the sub-device context.
        :type dy: int
        :param reg_max: If True (default), the sub-device context will automatically
            update the maximum width and height of the device context.
        :type reg_max: bool
        """
        self.x = parent.x + x
        self.y = parent.y + y
        self.dx = dx
        self.dy = dy
        if parent.__class__ == SubDc:
            self._parent = parent._parent
        else:
            self._parent = parent
        if reg_max:
            self._parent.test_point(self.x + self.dx, self.y + self.dy)

    def subdc(
        self,
        x,
        y,
        dx,
        dy,
        reg_max=True,
    ):
        """
        Creates a sub-device context (SubDc) for the current device context.

        The sub-device context is defined by its top-left corner (x,y), width (dx) and height (dy) in points.

        :param x: The x-coordinate of the top-left corner of the sub-device context.
        :type x: int
        :param y: The y-coordinate of the top-left corner of the sub-device context.
        :type y: int
        :param dx: The width of the sub-device context.
        :type dx: int
        :param dy: The height of the sub-device context.
        :type dy: int
        :param reg_max: If True (default), the sub-device context will automatically
            update the maximum width and height of the device context.
        :type reg_max: bool
        :return: The created sub-device context
        :rtype: SubDc
        """
        return SubDc(self, x, y, dx, dy, reg_max)

    def get_size(self):
        """
        Returns the size of the device context as a list of two elements: the width and the height.

        :return: The size of the device context
        :rtype: list
        """
        return [self.dx, self.dy]

    def __getattribute__(self, attr):
        """
        Overrides the standard __getattribute__ method to allow for chaining of device contexts.

        If the attribute is not found in the current device context, it will be searched in the parent device context.

        :param attr: The name of the attribute to be retrieved.
        :type attr: str
        :return: The requested attribute
        :rtype: object
        """
        try:
            ret = object.__getattribute__(self, attr)
        except:
            ret = getattr(self._parent, attr)
        return ret

    def play_str(self, str):
        """
        Replays a string of actions in the sub-device context.

        The input string is expected to be a newline-separated list of
        method calls. Each method call is represented as a string where
        the method name is followed by its arguments enclosed in parentheses.
        If there are multiple arguments, they are separated by commas.

        :param str: The string of actions to replay.
        :type str: str
        :return: None
        """

        for buf in str.split("\n"):
            buf = buf.strip()
            if buf != "":
                pos = buf.split("(")
                if len(pos) > 2:
                    pos2 = []
                    pos2.append(pos[0])
                    pos2.append("".s.join(pos[1:]))
                    pos = pos2
                if len(pos) == 2:
                    name = pos[0]
                    attr = (pos[1])[:-1]
                    if attr == "":
                        attr = None
                    else:
                        attr = json_loads("[" + attr + "]")
                    fun = getattr(self, name)
                    if attr:
                        fun(*attr)
                    else:
                        fun()

    @convert_fun_arg
    def add_line(self, x, y, dx, dy):
        """
        Adds a line to the sub-device context.

        This method calls the parent device context's `add_line` method with the
        provided coordinates and dimensions, potentially adjusted by the
        `convert_fun_arg` decorator.

        :param x: The x-coordinate of the starting point of the line.
        :param y: The y-coordinate of the starting point of the line.
        :param dx: The horizontal length of the line.
        :param dy: The vertical length of the line.
        :return: None
        """
        return self._parent.add_line(x, y, dx, dy)

    @convert_fun_arg
    def add_rectangle(self, x, y, dx, dy):
        """
        Adds a rectangle to the sub-device context.

        This method calls the parent device context's `add_rectangle` method with the
        provided coordinates and dimensions, potentially adjusted by the
        `convert_fun_arg` decorator.

        :param x: The x-coordinate of the top-left corner of the rectangle.
        :param y: The y-coordinate of the top-left corner of the rectangle.
        :param dx: The width of the rectangle.
        :param dy: The height of the rectangle.
        :return: None
        """
        return self._parent.add_rectangle(x, y, dx, dy)

    @convert_fun_arg
    def add_rounded_rectangle(self, x, y, dx, dy, radius):
        """
        Adds a rounded rectangle to the sub-device context.

        This method calls the parent device context's `add_rounded_rectangle` method with the
        provided coordinates and dimensions, potentially adjusted by the
        `convert_fun_arg` decorator.

        :param x: The x-coordinate of the top-left corner of the rounded rectangle.
        :param y: The y-coordinate of the top-left corner of the rounded rectangle.
        :param dx: The width of the rounded rectangle.
        :param dy: The height of the rounded rectangle.
        :param radius: The radius of the rounded corners.
        :return: None
        """
        return self._parent.add_rounded_rectangle(x, y, dx, dy, radius)

    @convert_fun_arg
    def add_arc(self, x, y, radius, angle1, angle2):
        """
        Adds an arc to the sub-device context.

        This method calls the parent device context's `add_arc` method with the
        provided coordinates and dimensions, potentially adjusted by the
        `convert_fun_arg` decorator.

        :param x: The x-coordinate of the center of the arc.
        :param y: The y-coordinate of the center of the arc.
        :param radius: The radius of the arc.
        :param angle1: The starting angle of the arc in degrees.
        :param angle2: The ending angle of the arc in degrees.
        :return: None
        """
        return self._parent.add_arc(x, y, radius, angle1, angle2)

    @convert_fun_arg
    def add_ellipse(self, x, y, dx, dy):
        """
        Adds an ellipse to the sub-device context.

        This method calls the parent device context's `add_ellipse` method with the
        provided coordinates and dimensions, potentially adjusted by the
        `convert_fun_arg` decorator.

        :param x: The x-coordinate of the center of the ellipse.
        :param y: The y-coordinate of the center of the ellipse.
        :param dx: The horizontal diameter of the ellipse.
        :param dy: The vertical diameter of the ellipse.
        :return: None
        """
        return self._parent.add_ellipse(x, y, dx, dy)

    def add_polygon(self, xytab):
        """
        Adds a polygon to the sub-device context.

        This method calls the parent device context's `add_polygon` method with the
        provided coordinates and dimensions, potentially adjusted by the
        `convert_fun_arg` decorator.

        :param xytab: A list of tuples with the x and y coordinates of the polygon's vertices.
        :return: None
        """
        xytab2 = []
        for pos in xytab:
            xytab2.append((self.x + pos[0], self.y + pos[1]))
        return self._parent.add_polygon(xytab2)

    def add_spline(self, xytab, close):
        """
        Adds a spline to the sub-device context.

        This method calls the parent device context's `add_spline` method with the
        provided coordinates and dimensions, potentially adjusted by the
        `convert_fun_arg` decorator.

        :param xytab: A list of tuples with the x and y coordinates of the spline's vertices.
        :param close: A boolean indicating if the spline should be closed.
        :return: None
        """

        xytab2 = []
        for pos in xytab:
            xytab2.append((self.x + pos[0], self.y + pos[1]))
        return self._parent.add_spline(xytab2, close)

    @convert_fun_arg
    def draw_text(self, x, y, txt):
        """
        Draws a text string on the sub-device context.

        This method calls the parent device context's `draw_text` method with the
        provided coordinates and text, potentially adjusted by the
        `convert_fun_arg` decorator.

        :param x: The x-coordinate of the starting position of the text.
        :param y: The y-coordinate of the starting position of the text.
        :param txt: The text string to be drawn.
        :return: None
        """
        return self._parent.draw_text(x, y, txt)

    @convert_fun_arg
    def draw_rotated_text(self, x, y, txt, angle):
        """
        Draws a rotated text string on the sub-device context.

        This method calls the parent device context's `draw_rotated_text` method with the
        provided coordinates, text and angle, potentially adjusted by the
        `convert_fun_arg` decorator.

        :param x: The x-coordinate of the starting position of the text.
        :param y: The y-coordinate of the starting position of the text.
        :param txt: The text string to be drawn.
        :param angle: The angle of rotation in degrees.
        :return: None
        """
        return self._parent.draw_rotated_text(x, y, txt, angle)

    @convert_fun_arg
    def draw_image(self, x, y, dx, dy, scale, png_data):
        """
        Draws an image on the sub-device context.

        This method calls the parent device context's `draw_image` method with the
        provided coordinates and image data, potentially adjusted by the
        `convert_fun_arg` decorator.

        :param x: The x-coordinate of the top-left corner of the image.
        :param y: The y-coordinate of the top-left corner of the image.
        :param dx: The width of the image.
        :param dy: The height of the image.
        :param scale: The scale factor of the image.
        :param png_data: The image data in PNG format.
        :return: None
        """
        return self._parent.draw_image(x, y, dx, dy, scale, png_data)

    @convert_fun_arg
    def draw_atom_line(self, x, y, line):
        """
        Draws a line of atoms on the sub-device context.

        This method calls the parent device context's `draw_atom_line` method with the
        provided coordinates and line of atoms, potentially adjusted by the
        `convert_fun_arg` decorator.

        :param x: The x-coordinate of the starting point of the line.
        :param y: The y-coordinate of the starting point of the line.
        :param line: A :class:`Line` instance representing the line of atoms to be drawn.
        :return: None
        """
        return self._parent.draw_atom_line(x, y, line)


class NullDc(object):
    def __init__(self, ref_dc):
        """
        Initializes the NullDc instance.

        :param ref_dc: The reference device context.
        :type ref_dc: BaseDc or SubDc
        """

        self._ref_dc = ref_dc
        self._maxwidth = 0
        self._maxheight = 0

    def __getattribute__(self, attr):
        """
        Overrides the standard __getattribute__ method to allow for chaining of device contexts.

        If the attribute is not found in the current device context, it will be searched in the parent device context.

        :param attr: The name of the attribute to be retrieved.
        :type attr: str
        :return: The requested attribute
        :rtype: object
        """
        if attr.startswith("_"):
            ret = object.__getattribute__(self, attr)
        else:
            try:
                ret = object.__getattribute__(self, attr)
            except:
                ret = getattr(self._ref_dc, attr)
        return ret

    def get_dc_info(self):
        """
        Returns the device context information for the referenced device context.

        :return: The device context information of the referenced device context.
        :rtype: BaseDcInfo
        """
        return self._ref_dc.dc_info

    def get_max_sizes(self):
        """
        Returns the maximum width and height of the document content in points.

        :rtype: tuple
        :return: A tuple (width, height) containing the maximum width and height of the document content in points.
        """
        return (self._maxwidth, self._maxheight)

    def test_point(self, x, y):
        """
        Tests if a point is within the document's maximum size.

        :param x: The x-coordinate of the point
        :param y: The y-coordinate of the point
        :return: None
        """
        if x > 10000000 or y > 1000000:
            return
        if x > self._maxwidth:
            self._maxwidth = x
        if y > self._maxheight:
            self._maxheight = y

    def subdc(self, x, y, dx, dy, reg_max=True):
        """
        Creates a sub-device context (SubDc) for the current device context.

        :param x: The x-coordinate of the top-left corner of the sub-device context.
        :type x: int
        :param y: The y-coordinate of the top-left corner of the sub-device context.
        :type y: int
        :param dx: The width of the sub-device context.
        :type dx: int
        :param dy: The height of the sub-device context.
        :type dy: int
        :param reg_max: If True (default), the sub-device context will automatically
            update the maximum width and height of the device context.
        :type reg_max: bool
        :return: The created sub-device context
        :rtype: SubDc
        """
        return SubDc(self, x, y, dx, dy, reg_max)

    def add_line(self, x, y, dx, dy):
        """
        Adds a line to the device context.

        The line is defined by its starting point (x,y) and its horizontal and vertical lengths (dx,dy).

        :param x: The x-coordinate of the starting point of the line.
        :param y: The y-coordinate of the starting point of the line.
        :param dx: The horizontal length of the line.
        :param dy: The vertical length of the line.
        :return: None
        """
        self.test_point(x + dx, y + dy)
        return None

    def add_rectangle(self, x, y, dx, dy):
        """
        Adds a rectangle to the device context.

        The rectangle is defined by its top-left corner (x,y) and its width and height (dx,dy).

        :param x: The x-coordinate of the top-left corner of the rectangle.
        :param y: The y-coordinate of the top-left corner of the rectangle.
        :param dx: The width of the rectangle.
        :param dy: The height of the rectangle.
        :return: None
        """
        self.test_point(x + dx, y + dy)
        return None

    def add_rounded_rectangle(self, x, y, dx, dy, radius):
        """
        Adds a rounded rectangle to the device context.

        The rounded rectangle is defined by its top-left corner (x,y), its width and height (dx,dy), and its corner radius.

        :param x: The x-coordinate of the top-left corner of the rectangle.
        :param y: The y-coordinate of the top-left corner of the rectangle.
        :param dx: The width of the rectangle.
        :param dy: The height of the rectangle.
        :param radius: The radius of the rounded corners.
        :return: None
        """
        self.test_point(x + dx, y + dy)
        return None

    def add_arc(self, x, y, radius, angle1, angle2):
        """
        Adds an arc to the device context.

        The arc is defined by its center (x,y), its radius, and the starting and ending angles of the arc.

        :param x: The x-coordinate of the center of the arc.
        :param y: The y-coordinate of the center of the arc.
        :param radius: The radius of the arc.
        :param angle1: The starting angle of the arc in degrees.
        :param angle2: The ending angle of the arc in degrees.
        :return: None
        """
        self.test_point(x + radius, y + radius)
        return None

    def add_ellipse(self, x, y, dx, dy):
        """
        Adds an ellipse to the device context.

        This method computes the bounding box of the ellipse defined by its center
        (x, y) and its horizontal and vertical diameters (dx, dy), and ensures
        that the bounding box fits within the document's maximum dimensions.

        :param x: The x-coordinate of the center of the ellipse.
        :param y: The y-coordinate of the center of the ellipse.
        :param dx: The horizontal diameter of the ellipse.
        :param dy: The vertical diameter of the ellipse.
        :return: None
        """

        self.test_point(x + dx, y + dy)
        return None

    def add_polygon(self, xytab):
        """
        Adds a polygon to the device context.

        This method ensures that each vertex of the polygon, specified by the list
        of (x, y) coordinates in `xytab`, is within the document's maximum dimensions.

        :param xytab: A list of tuples, where each tuple contains the x and y
                    coordinates of a vertex of the polygon.
        :return: None
        """
        for pos in xytab:
            self.test_point(pos[0], pos[1])
        return None

    def add_spline(self, xytab, close):
        """
        Adds a spline to the device context.

        This method ensures that each vertex of the spline, specified by the list
        of (x, y) coordinates in `xytab`, is within the document's maximum dimensions.

        :param xytab: A list of tuples, where each tuple contains the x and y
                    coordinates of a vertex of the spline.
        :param close: A boolean indicating if the spline should be closed.
        :return: None
        """
        for pos in xytab:
            self.test_point(pos[0], pos[1])
        return None

    def draw_text(self, x, y, txt):
        """
        Draws text at the specified coordinates.

        This method ensures the given coordinates are within the document's maximum size
        by calling `test_point`.

        :param x: The x-coordinate of the starting position of the text.
        :param y: The y-coordinate of the starting position of the text.
        :param txt: The text string to be drawn.
        :return: None
        """
        self.test_point(x, y)
        return None

    def draw_rotated_text(self, x, y, txt, angle):
        """
        Draws rotated text at the specified coordinates.

        This method ensures the given coordinates are within the document's maximum size
        by calling `test_point`.

        :param x: The x-coordinate of the starting position of the text.
        :param y: The y-coordinate of the starting position of the text.
        :param txt: The text string to be drawn.
        :param angle: The angle of rotation in degrees.
        :return: None
        """
        self.test_point(x, y)
        return None

    def draw_image(self, x, y, dx, dy, scale, png_data):
        """
        Draws an image at the specified coordinates.

        This method ensures the given coordinates are within the document's maximum size
        by calling `test_point`.

        :param x: The x-coordinate of the top-left corner of the image.
        :param y: The y-coordinate of the top-left corner of the image.
        :param dx: The width of the image.
        :param dy: The height of the image.
        :param scale: The scale factor of the image.
        :param png_data: The image data in PNG format.
        :return: None
        """
        self.test_point(x + dx, y + dy)
        return None


class NullDcinfo(object):
    def __init__(self, dc):
        """
        Initializes the NullDcinfo instance.

        :param dc: The device context associated with this NullDcinfo instance.
        :type dc: NullDc
        """
        pass

    def get_text_width(self, txt, style):
        """
        Calculates the width of the text in the given style.

        :param txt: The text to measure.
        :param style: The style to use for the measurement.
        :return: The width of the text in the given style.
        """
        return 12 * len(txt)

    def get_text_height(self, txt, style):
        """
        Calculates the height of the given text in the specified style.

        :param txt: The text to measure.
        :param style: The style to use for the measurement.
        :return: The height of the text in the given style.
        """
        return 12

    def get_line_dy(self, height):
        """
        Calculates the line spacing for the given line height.

        :param height: The line height.
        :return: The line spacing.
        """
        return height * 12

    def get_multiline_text_width(self, txt, style="default"):
        """
        Calculates the optimal, minimum, and maximum text widths for multiline text.

        This function splits the input text into individual words, calculates the width
        of each word, and determines the minimum and maximum widths. It also calculates
        an optimal width based on the total text width, limited by a factor of 16 if
        the number of words exceeds 16.

        :param txt: The input text to measure.
        :param style: The style to use for the measurement (default is "default").
        :return: A tuple (optsize, minsize, maxsize) representing the optimal, minimum,
                and maximum widths of the text.
        """
        return 100

    def get_multiline_text_height(self, txt, width, style="default"):
        """
        Calculates the height of the given multiline text and the text lines.

        This function splits the input text into individual words, checks if the width
        of each word exceeds the given width, and if so, adds the current line to the
        output list and resets the line to the current word. It also keeps track of the
        total height of the text.

        :param txt: The input text to measure.
        :param width: The width to check against.
        :param style: The style to use for the measurement (default is "default").
        :return: A tuple (height, lines) representing the height of the text and a list
                of the individual text lines.
        """
        return (100, [])

    def get_extents(self, word, style):
        """
        Calculates the text extents for a given word and style.

        :param word: The word to calculate the text extents for.
        :param style: The style to use for the calculation.
        :return: A tuple (dx, dx_space, dy_up, dy_down) representing the width of the
                word, the width of a space, the vertical offset for the top of the
                text, and the vertical offset for the bottom of the text.
        """
        return (100, 0, 0, 20)

    def get_style_id(self, style):
        """
        Returns an ID for the given style.

        The ID is a zero-based index into the list of styles. If the style is not
        already in the list, it will be added and the new ID will be returned.

        :param style: The style for which to return an ID.
        :return: The ID of the style.
        """
        return 0
