import sys
from pathlib import Path

# Import necessary modules
from pytigon_lib.schhtml.pdfdc import PdfDc
from pytigon_lib.schhtml.cairodc import CairoDc
from pytigon_lib.schhtml.htmlviewer import HtmlViewerParser


def main():
    try:
        # Configuration
        run_cairo = False
        css_file_path = Path("./test/icss/form.icss")
        output_pdf_path = Path("test/test.pdf")
        default_html_file = "test/test11.html"

        # Read initial CSS
        if not css_file_path.exists():
            raise FileNotFoundError(f"CSS file not found: {css_file_path}")
        init_css_str = css_file_path.read_text()

        # Determine HTML file to process
        name = sys.argv[1] if len(sys.argv) > 1 else default_html_file
        html_file_path = Path(name)
        if not html_file_path.exists():
            raise FileNotFoundError(f"HTML file not found: {html_file_path}")

        # Set dimensions for the output
        width, height = 595, 842

        # Initialize the appropriate drawing context
        dc = (
            CairoDc(
                calc_only=False,
                width=width,
                height=height,
                output_name=str(output_pdf_path),
            )
            if run_cairo
            else PdfDc(
                calc_only=False,
                width=width,
                height=height,
                output_name=str(output_pdf_path),
            )
        )

        # Configure paging
        dc.set_paging(False)
        dc.set_paging(True)

        # Initialize HTML parser
        p = HtmlViewerParser(
            dc=dc, calc_only=False, init_css_str=init_css_str, css_type=1
        )

        # Process HTML file
        with html_file_path.open("rb") as f:
            for line in f:
                p.feed(line.decode("utf-8"))

        # Finalize the document
        p.close()
        dc.end_page()

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        sys.exit(1)


import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys


def test_main_success():
    with (
        patch("builtins.open", MagicMock()) as mock_open,
        patch("pathlib.Path.read_text", return_value="dummy_css"),
        patch("pytigon_lib.schhtml.pdfdc.PdfDc") as mock_pdf_dc,
        patch("pytigon_lib.schhtml.htmlviewer.HtmlViewerParser") as mock_parser,
    ):
        # Mock the file existence
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        with patch("pathlib.Path", return_value=mock_path):
            main()

        # Assertions to ensure the correct methods were called
        mock_pdf_dc.assert_called_once()
        mock_parser.assert_called_once()


def test_main_file_not_found():
    with (
        patch("pathlib.Path.exists", return_value=False),
        pytest.raises(FileNotFoundError),
    ):
        main()


def test_main_general_exception():
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch("pathlib.Path.read_text", side_effect=Exception("Test Exception")),
        pytest.raises(Exception),
    ):
        main()
