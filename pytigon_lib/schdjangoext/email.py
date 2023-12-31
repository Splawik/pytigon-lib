import email

from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template
from django.template import Template, Context
from email.mime.text import MIMEText
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

    def set_eml_body(self, context, eml_template_name, txt_template_name=None):
        template_eml = get_template(eml_template_name)
        eml_name = template_eml.origin.name
        with open(eml_name, "rt") as f:
            t = Template(f.read())
            c = Context(context)
            txt = t.render(c)
            msg = email.message_from_string(txt)
            self.attach(content=msg, mimetype="message/rfc822")


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
    if message_template_name.endswith(".eml"):
        message.set_eml_body(context, message_template_name)
    if prepare_message:
        prepare_message(message)
    if send:
        message.send()
    return message
