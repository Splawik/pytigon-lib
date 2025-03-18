import os
import datetime
import tempfile
import pathlib

from pytigon_lib.schdjangoext.spreadsheet_render import render_ooxml, render_odf
from pytigon_lib.schtools.doc_tools import soffice_convert
from pytigon_lib.schtest.html_test import html_content_cmp
from django.conf import settings


TEST_PATH = pathlib.Path(__file__).parent.resolve()

in_file_path = os.path.join(TEST_PATH, "assets/rep_wzr.xlsx")
out_file_path = os.path.join(tempfile.gettempdir(), "rep_wzr_out.xlsx")


def test_gen_doc():
    context = {
        "spreadsheets": ["X1", "X2", "X3"],
        "object_list": [
            [1, 1.5, "Hello world!", datetime.datetime.now()],
            [2, 2.5, "Hello world!", datetime.datetime.now()],
            [3, 3.5, "Hello world!", datetime.datetime.now()],
        ],
    }
    render_ooxml(in_file_path, context, out_file_path)
    render_odf(
        in_file_path.replace(".xlsx", ".ods"),
        context,
        out_file_path.replace(".xlsx", ".ods"),
    )
    soffice_convert(
        out_file_path,
        out_file_path + ".html",
        "html",
    )
    soffice_convert(
        out_file_path.replace(".xlsx", ".ods"),
        out_file_path.replace(".xlsx", ".ods.html"),
        "html",
    )

    cmp1 = html_content_cmp(
        out_file_path + ".html",
        in_file_path.replace("assets/rep_wzr.xlsx", "wzr/rep_wzr_out.xlsx.html"),
    )
    cmp2 = html_content_cmp(
        out_file_path.replace(".xlsx", ".ods.html"),
        in_file_path.replace("assets/rep_wzr.xlsx", "wzr/rep_wzr_out.ods.html"),
    )

    assert (True if cmp1 and cmp2 else False) == True


if __name__ == "__main__":
    test_gen_doc()
