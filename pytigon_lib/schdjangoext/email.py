from django.core.mail import EmailMultiAlternatives
from django.template.loader import get_template


class PytigonEmailMessage(EmailMultiAlternatives):
    def __init__(self, *argi, **argv):
        super().__init__(*argi, **argv)
        self.html_body = None

    def set_body(self, context, html_template_name, txt_template_name=None):
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


def send_message(
    subject,
    message_html_template_name,
    from_email,
    to,
    bcc,
    context={},
    message_txt_template_name=None,
    prepare_message=None,
):
    message = PytigonEmailMessage(subject, "", from_email, to, bcc)
    if message_html_template_name:
        message.set_body(context, message_html_template_name, message_txt_template_name)
    if prepare_message:
        prepare_message(message)
    message.send()
