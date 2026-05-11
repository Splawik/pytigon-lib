"""Email utilities extending Django's EmailMultiAlternatives.

Provides :class:`PytigonEmailMessage` which adds support for
HTML templates, plain-text fallback, and EML template rendering.
"""

import email
from email.mime.image import MIMEImage

from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.template import Template, Context


def _extract_charset(content_type_header, default="utf-8"):
    """Extract the charset from a Content-Type header value.

    Handles both ``charset=utf-8`` and ``charset="utf-8"`` formats.

    Args:
        content_type_header: The value of the Content-Type header.
        default: Fallback charset if none is found.

    Returns:
        The extracted charset string (lowercased).
    """
    if not content_type_header:
        return default
    # Try quoted form first: charset="utf-8"
    if 'charset="' in content_type_header.lower():
        try:
            start = content_type_header.lower().index('charset="') + len('charset="')
            end = content_type_header.index('"', start)
            return content_type_header[start:end].lower()
        except (ValueError, IndexError):
            pass
    # Try unquoted form: charset=utf-8
    if "charset=" in content_type_header.lower():
        try:
            start = content_type_header.lower().index("charset=") + len("charset=")
            charset = content_type_header[start:].split(";")[0].strip().lower()
            if charset:
                return charset
        except (ValueError, IndexError):
            pass
    return default


class PytigonEmailMessage(EmailMultiAlternatives):
    """Extended EmailMultiAlternatives with HTML and EML template support.

    Supports rendering Django templates for both HTML and plain-text
    bodies, as well as processing .eml templates with embedded images
    and attachments.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.html_body = None

    def set_html_body(self, context, html_template_name, txt_template_name=None):
        """Render HTML (and optional plain-text) templates and attach them.

        Args:
            context: Template context dictionary.
            html_template_name: Django template name for the HTML body.
            txt_template_name: Optional plain-text template name. If not
                given, derived by replacing ``.html`` with ``.txt`` in
                ``html_template_name``.

        Raises:
            ValueError: If template loading or rendering fails.
        """
        try:
            template_html = get_template(html_template_name)
            txt_template_name = txt_template_name or html_template_name.replace(
                ".html", ".txt"
            )
            template_plain = get_template(txt_template_name)

            self.html_body = template_html.render(context)
            self.body = template_plain.render(context)
            self.attach_alternative(self.html_body, "text/html")
        except Exception as e:
            raise ValueError(f"Error setting HTML body: {e}") from e

    def _process_part(self, part):
        """Recursively process a single MIME part of an EML message.

        Handles multipart containers, text parts (plain and HTML),
        inline images, and generic attachments.

        Args:
            part: A :class:`~email.message.Message` part.
        """
        maintype = part.get_content_maintype()

        if maintype == "multipart":
            for item in part.get_payload():
                self._process_part(item)

        elif maintype == "text" and not self.html_body:
            content_type = part.get_content_type()
            encoding = _extract_charset(part.get("Content-Type", ""))
            payload = part.get_payload(decode=True)

            if payload is None:
                return

            try:
                decoded = payload.decode(encoding)
            except (UnicodeDecodeError, LookupError):
                decoded = payload.decode("utf-8", errors="replace")

            if content_type == "text/plain":
                self.body = decoded
            else:
                self.attach_alternative(decoded, content_type)
                self.html_body = "OK"

        elif maintype == "image":
            payload = part.get_payload(decode=True)
            if payload is not None:
                img = MIMEImage(payload)
                for key, value in part.items():
                    img.add_header(key, value)
                self.attach(img)

        else:
            self.attach(part)

    def set_eml_body(self, context, eml_template_name):
        """Set the email body from an EML template file.

        The template is rendered as a Django template and then parsed
        as a complete EML message, preserving multipart structure,
        attachments, and inline images.

        Args:
            context: Template context dictionary.
            eml_template_name: Django template name for the EML source.

        Raises:
            ValueError: If template loading, rendering, or parsing fails.
        """
        try:
            template_eml = get_template(eml_template_name)
            eml_name = template_eml.origin.name
            with open(eml_name, "rt", encoding="utf-8") as f:
                t = Template(f.read())
                c = Context(context)
                txt = t.render(c)
                self._process_part(email.message_from_string(txt))
        except Exception as e:
            raise ValueError(f"Error setting EML body: {e}") from e


def send_message(
    subject,
    message_template_name,
    from_email,
    to,
    bcc=None,
    context=None,
    message_txt_template_name=None,
    prepare_message=None,
    send=True,
):
    """Convenience function to create and send a PytigonEmailMessage.

    Args:
        subject: Email subject line.
        message_template_name: Django template name (``.html`` or
            ``.eml`` extension determines processing mode).
        from_email: Sender address.
        to: Recipient list.
        bcc: Optional BCC list.
        context: Optional template context dictionary.
        message_txt_template_name: Explicit plain-text template name
            (only used for ``.html`` templates).
        prepare_message: Optional callback receiving the message
            instance before sending.
        send: If False, the message is returned without being sent.

    Returns:
        PytigonEmailMessage: The constructed (and possibly sent)
        message instance.

    Raises:
        ValueError: If message construction or sending fails.
    """
    if context is None:
        context = {}

    message = PytigonEmailMessage(subject, "", from_email, to, bcc)

    try:
        if message_template_name.endswith(".html"):
            message.set_html_body(
                context, message_template_name, message_txt_template_name
            )
        elif message_template_name.endswith(".eml"):
            message.set_eml_body(context, message_template_name)

        if prepare_message:
            prepare_message(message)

        if send:
            message.send()

        return message
    except Exception as e:
        raise ValueError(f"Error sending message: {e}") from e
