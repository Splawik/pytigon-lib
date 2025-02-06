import email
from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.template import Template, Context
from email.mime.image import MIMEImage


class PytigonEmailMessage(EmailMultiAlternatives):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.html_body = None

    def set_html_body(self, context, html_template_name, txt_template_name=None):
        """Set the HTML and plain text body of the email."""
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
            raise ValueError(f"Error setting HTML body: {e}")

    def _process_part(self, part):
        """Process each part of the email message."""
        if part.get_content_maintype() == "multipart":
            for item in part.get_payload():
                self._process_part(item)
        elif part.get_content_maintype() == "text" and not self.html_body:
            encoding = (
                part.get("Content-Type", "").split('"')[1]
                if '"' in part.get("Content-Type", "")
                else "utf-8"
            )
            if part.get_content_type() == "text/plain":
                self.body = part.get_payload(decode=True).decode(encoding)
            else:
                self.attach_alternative(
                    part.get_payload(decode=True).decode(encoding),
                    part.get_content_type(),
                )
                self.html_body = "OK"
        elif part.get_content_maintype() == "image":
            img = MIMEImage(part.get_payload(decode=True))
            for key, value in part.items():
                img.add_header(key, value)
            self.attach(img)
        else:
            self.attach(part)

    def set_eml_body(self, context, eml_template_name):
        """Set the email body from an EML template."""
        try:
            template_eml = get_template(eml_template_name)
            eml_name = template_eml.origin.name
            with open(eml_name, "rt") as f:
                t = Template(f.read())
                c = Context(context)
                txt = t.render(c)
                self._process_part(email.message_from_string(txt))
        except Exception as e:
            raise ValueError(f"Error setting EML body: {e}")


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
    """Send an email message."""
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
        raise ValueError(f"Error sending message: {e}")
