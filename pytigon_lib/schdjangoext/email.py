import email

from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.template import Template, Context
from email.mime.image import MIMEImage


class PytigonEmailMessage(EmailMultiAlternatives):
    def __init__(self, *argi, **argv):
        super().__init__(*argi, **argv)
        self.html_body = None

    def set_html_body(self, context, html_template_name, txt_template_name=None):
        template_html = get_template(html_template_name)
        txt_template_name2 = (
            txt_template_name
            if txt_template_name
            else html_template_name.replace(".html", ".txt")
        )
        template_plain = get_template(txt_template_name2)
        self.html_body = template_html.render(context)
        self.body = template_plain.render(context)
        self.attach_alternative(self.html_body, "text/html")

    def _process_part(self, part):
        if part.get_content_maintype() == "multipart":
            for item in part.get_payload():
                self._process_part(item)
        elif part.get_content_maintype() == "text" and not self.html_body:
            try:
                encoding = part.get("Content-Type").split('"')[1]
            except:
                encoding = "utf-8"
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
            for item in part.items():
                img.add_header(item[0], item[1])
            self.attach(img)
        else:
            self.attach(part, "message/rfc822")

    def set_eml_body(self, context, eml_template_name):
        template_eml = get_template(eml_template_name)
        eml_name = template_eml.origin.name
        with open(eml_name, "rt") as f:
            t = Template(f.read())
            c = Context(context)
            txt = t.render(c)
            self._process_part(email.message_from_string(txt))


def send_message(
    subject,
    message_template_name,
    from_email,
    to,
    bcc,
    context={},
    message_txt_template_name=None,
    prepare_message=None,
    send=True,
):
    message = PytigonEmailMessage(subject, "", from_email, to, bcc)
    if message_template_name.endswith(".html"):
        message.set_html_body(context, message_template_name, message_txt_template_name)
    elif message_template_name.endswith(".eml"):
        message.set_eml_body(context, message_template_name)
    if prepare_message:
        prepare_message(message)
    if send:
        message.send()
    return message
