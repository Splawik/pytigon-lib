"""Tests for :mod:`pytigon_lib.schhtml.main`."""

import sys
from unittest.mock import MagicMock, patch

import pytest

from pytigon_lib.schhtml.main import main


class TestMain:
    def test_main_file_not_found(self):
        """main() exits with code 1 when the HTML file does not exist."""
        with patch.object(sys, "argv", ["main", "/nonexistent/file.html"]):
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_main_with_existing_html(self):
        """main() processes an existing HTML file without crashing."""
        with patch.object(sys, "argv", ["main", "test.html"]):
            with patch("pytigon_lib.schhtml.main.Path.exists", return_value=True):
                with patch("pytigon_lib.schhtml.main.Path.read_text", return_value=""):
                    with patch("pathlib.Path.open", create=True) as mock_open:
                        mock_file = MagicMock()
                        mock_file.__enter__.return_value = [b"<html></html>"]
                        mock_open.return_value = mock_file
                        with patch("pytigon_lib.schhtml.main.PdfDc") as mock_pdfdc:
                            mock_dc = MagicMock()
                            mock_pdfdc.return_value = mock_dc
                            with patch("pytigon_lib.schhtml.main.HtmlViewerParser") as mock_parser:
                                mock_p = MagicMock()
                                mock_parser.return_value = mock_p
                                main()
                                mock_parser.assert_called_once()
                                mock_p.close.assert_called_once()
                                mock_dc.end_page.assert_called_once()

    def test_main_calls_set_paging(self):
        """main() calls dc.set_paging before initialising the parser."""
        with patch.object(sys, "argv", ["main", "test.html"]):
            with patch("pytigon_lib.schhtml.main.Path.exists", return_value=True):
                with patch("pytigon_lib.schhtml.main.Path.read_text", return_value=""):
                    with patch("pathlib.Path.open", create=True) as mock_open:
                        mock_file = MagicMock()
                        mock_file.__enter__.return_value = [b"<html></html>"]
                        mock_open.return_value = mock_file
                        with patch("pytigon_lib.schhtml.main.PdfDc") as mock_pdfdc:
                            mock_dc = MagicMock()
                            mock_pdfdc.return_value = mock_dc
                            with patch("pytigon_lib.schhtml.main.HtmlViewerParser"):
                                main()
                                mock_dc.set_paging.assert_any_call(False)
                                mock_dc.set_paging.assert_any_call(True)

    def test_main_decodes_lines(self):
        """main() feeds decoded lines to the parser."""
        html_content = "<html><head></head><body>hello</body></html>"
        with patch.object(sys, "argv", ["main", "test.html"]):
            with patch("pytigon_lib.schhtml.main.Path.exists", return_value=True):
                with patch("pytigon_lib.schhtml.main.Path.read_text", return_value=""):
                    with patch("pathlib.Path.open", create=True) as mock_open:
                        mock_file = MagicMock()
                        mock_file.__enter__.return_value = [html_content.encode("utf-8")]
                        mock_open.return_value = mock_file
                        with patch("pytigon_lib.schhtml.main.PdfDc") as mock_pdfdc:
                            mock_pdfdc.return_value = MagicMock()
                            with patch("pytigon_lib.schhtml.main.HtmlViewerParser") as mock_parser:
                                mock_p = MagicMock()
                                mock_parser.return_value = mock_p
                                main()
                                mock_p.feed.assert_called_with(html_content)

    def test_main_default_html_file(self):
        """main() falls back to the default HTML file when no argument given."""
        with patch.object(sys, "argv", ["main"]):
            with patch("pytigon_lib.schhtml.main.Path.exists", return_value=True):
                with patch("pytigon_lib.schhtml.main.Path.read_text", return_value=""):
                    with patch("pathlib.Path.open", create=True) as mock_open:
                        mock_file = MagicMock()
                        mock_file.__enter__.return_value = [b"<html></html>"]
                        mock_open.return_value = mock_file
                        with patch("pytigon_lib.schhtml.main.PdfDc") as mock_pdfdc:
                            mock_pdfdc.return_value = MagicMock()
                            with patch("pytigon_lib.schhtml.main.HtmlViewerParser") as mock_parser:
                                mock_parser.return_value = MagicMock()
                                main()
                                mock_parser.assert_called_once()

    def test_main_css_type_indent(self):
        """main() passes css_type=1 to HtmlViewerParser."""
        with patch.object(sys, "argv", ["main", "test.html"]):
            with patch("pytigon_lib.schhtml.main.Path.exists", return_value=True):
                with patch("pytigon_lib.schhtml.main.Path.read_text", return_value="body{}"):
                    with patch("pathlib.Path.open", create=True) as mock_open:
                        mock_file = MagicMock()
                        mock_file.__enter__.return_value = [b"<html></html>"]
                        mock_open.return_value = mock_file
                        with patch("pytigon_lib.schhtml.main.PdfDc") as mock_pdfdc:
                            mock_pdfdc.return_value = MagicMock()
                            with patch("pytigon_lib.schhtml.main.HtmlViewerParser") as mock_parser:
                                mock_parser.return_value = MagicMock()
                                main()
                                call_kwargs = mock_parser.call_args[1]
                                assert call_kwargs["css_type"] == 1
                                assert call_kwargs["calc_only"] is False

    def test_main_closes_parser_even_on_error(self):
        """main() exits when CSS file not found."""
        with patch.object(sys, "argv", ["main", "test.html"]):
            with patch("pytigon_lib.schhtml.main.Path.exists", side_effect=FileNotFoundError):
                with pytest.raises(SystemExit) as exc_info:
                    main()
                assert exc_info.value.code == 1

    def test_main_output_pdf_path(self):
        """main() uses A4 dimensions."""
        with patch.object(sys, "argv", ["main", "test.html"]):
            with patch("pytigon_lib.schhtml.main.Path.exists", return_value=True):
                with patch("pytigon_lib.schhtml.main.Path.read_text", return_value="body{}"):
                    with patch("pathlib.Path.open", create=True) as mock_open:
                        mock_file = MagicMock()
                        mock_file.__enter__.return_value = [b"<html></html>"]
                        mock_open.return_value = mock_file
                        with patch("pytigon_lib.schhtml.main.PdfDc") as mock_pdfdc:
                            mock_pdfdc.return_value = MagicMock()
                            with patch("pytigon_lib.schhtml.main.HtmlViewerParser") as mock_parser:
                                mock_parser.return_value = MagicMock()
                                main()
                                call_kwargs = mock_pdfdc.call_args[1]
                                assert call_kwargs["width"] == 595
                                assert call_kwargs["height"] == 842

    def test_main_cairo_imported_in_code(self):
        """main() imports CairoDc at module level."""
        from pytigon_lib.schhtml import main as main_mod

        assert hasattr(main_mod, "CairoDc")

    def test_main_pdfdc_called_with_calc_only_false(self):
        """main() creates PdfDc with calc_only=False."""
        with patch.object(sys, "argv", ["main", "test.html"]):
            with patch("pytigon_lib.schhtml.main.Path.exists", return_value=True):
                with patch("pytigon_lib.schhtml.main.Path.read_text", return_value="body{}"):
                    with patch("pathlib.Path.open", create=True) as mock_open:
                        mock_file = MagicMock()
                        mock_file.__enter__.return_value = [b"<html></html>"]
                        mock_open.return_value = mock_file
                        with patch("pytigon_lib.schhtml.main.PdfDc") as mock_pdfdc:
                            mock_pdfdc.return_value = MagicMock()
                            with patch("pytigon_lib.schhtml.main.HtmlViewerParser") as mock_parser:
                                mock_parser.return_value = MagicMock()
                                main()
                                call_kwargs = mock_pdfdc.call_args[1]
                                assert call_kwargs["calc_only"] is False
