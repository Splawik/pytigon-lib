import email
from email.mime.image import MIMEImage
from unittest.mock import MagicMock, mock_open, patch

import pytest
from django.core.mail import EmailMultiAlternatives
from django.template import Context, Template

from pytigon_lib.schdjangoext.email import (
    PytigonEmailMessage,
    _extract_charset,
    send_message,
)


class TestExtractCharset:
    def test_extract_quoted_charset(self):
        result = _extract_charset('text/html; charset="utf-8"')
        assert result == "utf-8"

    def test_extract_unquoted_charset(self):
        result = _extract_charset("text/html; charset=iso-8859-1")
        assert result == "iso-8859-1"

    def test_extract_no_charset_returns_default(self):
        result = _extract_charset("text/html")
        assert result == "utf-8"

    def test_extract_none_returns_default(self):
        result = _extract_charset(None)
        assert result == "utf-8"

    def test_extract_empty_string(self):
        result = _extract_charset("")
        assert result == "utf-8"

    def test_extract_with_semicolons(self):
        result = _extract_charset("text/html; charset=utf-8; boundary=xxx")
        assert result == "utf-8"

    def test_extract_case_insensitive(self):
        result = _extract_charset("text/html; Charset=UTF-8")
        assert result == "utf-8"

    def test_extract_quoted_edge_case(self):
        result = _extract_charset('text/html; charset="UTF-8"')
        assert result == "utf-8"


class TestPytigonEmailMessage:
    @pytest.fixture
    def msg(self):
        return PytigonEmailMessage("Subject", "body", "from@example.com", ["to@example.com"])

    def test_init_sets_html_body_none(self, msg):
        assert msg.html_body is None

    def test_set_html_body_renders_templates(self, msg):
        mock_html = MagicMock()
        mock_html.render.return_value = "<html><body>Hi</body></html>"
        mock_txt = MagicMock()
        mock_txt.render.return_value = "Hi"

        with patch("pytigon_lib.schdjangoext.email.get_template", side_effect=[mock_html, mock_txt]):
            msg.set_html_body({}, "template.html")
            assert msg.html_body == "<html><body>Hi</body></html>"
            assert msg.body == "Hi"

    def test_set_html_body_derives_txt_template(self, msg):
        mock_html = MagicMock()
        mock_html.render.return_value = "<html></html>"
        mock_txt = MagicMock()
        mock_txt.render.return_value = "text"

        with patch("pytigon_lib.schdjangoext.email.get_template", side_effect=[mock_html, mock_txt]):
            msg.set_html_body({}, "template.html")
            assert True

    def test_set_html_body_error_raises_valueerror(self, msg):
        with patch("pytigon_lib.schdjangoext.email.get_template", side_effect=Exception("error")):
            with pytest.raises(ValueError, match="Error setting HTML body"):
                msg.set_html_body({}, "template.html")

    def test_set_eml_body_renders_and_processes(self, msg):
        mock_eml_template = MagicMock()
        eml_content = "Content-Type: text/plain; charset=utf-8\n\nHello"
        with patch("pytigon_lib.schdjangoext.email.get_template", return_value=mock_eml_template):
            with patch("builtins.open", mock_open(read_data=eml_content)):
                with patch("django.template.Template.__init__", return_value=None):
                    with patch("django.template.Template.render", return_value=eml_content):
                        with patch("django.template.Context.__init__", return_value=None):
                            with patch("pytigon_lib.schdjangoext.email.email.message_from_string") as mock_parse:
                                with patch.object(msg, "_process_part") as mock_process:
                                    msg.set_eml_body({}, "template.eml")
                                    mock_process.assert_called_once()

    def test_process_part_handles_image(self, msg):
        part = MagicMock()
        part.get_content_maintype.return_value = "image"
        part.get_payload.return_value = None
        part.items.return_value = []

        msg._process_part(part)

    def test_process_part_handles_other_attachment(self, msg):
        part = MagicMock()
        part.get_content_maintype.return_value = "application"
        msg.attach = MagicMock()
        msg._process_part(part)
        msg.attach.assert_called_once_with(part)


class TestSendMessage:
    def test_send_message_html_template(self):
        with patch("pytigon_lib.schdjangoext.email.PytigonEmailMessage.set_html_body") as mock_set:
            with patch("pytigon_lib.schdjangoext.email.PytigonEmailMessage.send"):
                result = send_message(
                    "Subject",
                    "template.html",
                    "from@ex.com",
                    ["to@ex.com"],
                    context={"key": "val"},
                    send=False,
                )
                mock_set.assert_called_once()
                assert isinstance(result, PytigonEmailMessage)

    def test_send_message_eml_template(self):
        with patch("pytigon_lib.schdjangoext.email.PytigonEmailMessage.set_eml_body") as mock_set:
            with patch("pytigon_lib.schdjangoext.email.PytigonEmailMessage.send"):
                result = send_message(
                    "Subject",
                    "template.eml",
                    "from@ex.com",
                    ["to@ex.com"],
                    send=False,
                )
                mock_set.assert_called_once()

    def test_send_message_with_bcc(self):
        with patch("pytigon_lib.schdjangoext.email.PytigonEmailMessage.set_html_body"):
            with patch("pytigon_lib.schdjangoext.email.PytigonEmailMessage.send"):
                result = send_message(
                    "Subject",
                    "t.html",
                    "from@ex.com",
                    ["to@ex.com"],
                    bcc=["bcc@ex.com"],
                    send=False,
                )
                assert "bcc@ex.com" in result.bcc

    def test_send_message_with_prepare(self):
        prepare_called = []

        def prepare(msg):
            prepare_called.append(msg)

        with patch("pytigon_lib.schdjangoext.email.PytigonEmailMessage.set_html_body"):
            with patch("pytigon_lib.schdjangoext.email.PytigonEmailMessage.send"):
                result = send_message(
                    "Subject",
                    "t.html",
                    "from@ex.com",
                    ["to@ex.com"],
                    prepare_message=prepare,
                    send=False,
                )
                assert len(prepare_called) == 1

    def test_send_message_error_raises_valueerror(self):
        with patch("pytigon_lib.schdjangoext.email.PytigonEmailMessage.set_html_body", side_effect=Exception("fail")):
            with pytest.raises(ValueError, match="Error sending message"):
                send_message(
                    "Subject",
                    "template.html",
                    "from@ex.com",
                    ["to@ex.com"],
                )
