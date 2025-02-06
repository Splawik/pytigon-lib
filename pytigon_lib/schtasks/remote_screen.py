import logging
from html.parser import HTMLParser


class OnlyTxtParser(HTMLParser):
    """HTML parser that extracts and concatenates text content from HTML."""

    def __init__(self):
        super().__init__()
        self.txt = []

    def handle_data(self, data):
        """Append stripped text data to the list."""
        self.txt.append(data.strip())

    def to_txt(self):
        """Return concatenated text content."""
        return " ".join(self.txt)


def to_txt(html_txt):
    """Convert HTML text to plain text."""
    try:
        parser = OnlyTxtParser()
        parser.feed(html_txt)
        return parser.to_txt()
    except Exception as e:
        logging.error(f"Error converting HTML to text: {e}")
        return ""


class RemoteScreen:
    """Class for handling remote screen logging and printing."""

    def __init__(self, cproxy=None, direction="down"):
        """Initialize RemoteScreen with a proxy and direction."""
        self.cproxy = cproxy
        self.direction = direction

    def __enter__(self):
        """Enter the context manager."""
        self.raw_print("<div class='log'></div>===>>")
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager."""
        pass

    def raw_print(self, html_txt):
        """Print raw HTML text or send it via proxy."""
        if self.cproxy:
            self.cproxy.send_event(html_txt)
        else:
            print(html_txt)

    def _log(self, html_txt, p_class, log_func, operator):
        """Internal method to log messages with specified class and operator."""
        operator2 = (
            operator.replace(">>", "<<") if self.direction != "down" else operator
        )

        if self.cproxy:
            self.raw_print(f"<p class='{p_class}'>{html_txt}</p>{operator2}")
        else:
            if log_func:
                log_func(to_txt(html_txt))

    def log(self, html_txt):
        """Log a standard message."""
        self._log(html_txt, "log-line", logging.info, "===>>.log")

    def info(self, html_txt):
        """Log an informational message."""
        self._log(html_txt, "text-info", logging.info, "===>>.log")

    def warning(self, html_txt):
        """Log a warning message."""
        self._log(html_txt, "text-warning", logging.warning, "===>>.log")

    def error(self, html_txt):
        """Log an error message."""
        self._log(html_txt, "text-white bg-danger", logging.error, "===>>.log")
