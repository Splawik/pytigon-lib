import os
import tempfile

from django.core.files.storage import default_storage

from pytigon.pytigon_run import run
from pytigon_lib.schtest.html_test import html_content_cmp
from pytigon_lib.schtools.main_paths import get_main_paths
from pytigon_lib.schtools.images import compare_images
from pytigon_lib.schtools.doc_tools import soffice_convert

import pypdfium2 as pdfium
import PIL

os.environ["SCRIPT_MODE"] = "1"

PATHS = get_main_paths()

PRJ_PATH = PATHS["PRJ_PATH"]
PRJ_PATH_ALT = PATHS["PRJ_PATH_ALT"]

if os.path.exists(os.path.join(PRJ_PATH, "schscripts")):
    SCHSCRIPTS_PATH = os.path.join(PRJ_PATH, "schscripts")
else:
    SCHSCRIPTS_PATH = os.path.join(PRJ_PATH_ALT, "schscripts")
if os.path.exists(os.path.join(PRJ_PATH, "_schtest")):
    TEST_PATH = os.path.join(PRJ_PATH, "_schtest")
else:
    TEST_PATH = os.path.join(PRJ_PATH_ALT, "_schtest")

LAST_PATH = os.getcwd()
os.chdir(TEST_PATH)


def test_gen_pdf():
    tests = (
        (
            os.path.join(TEST_PATH, "tests", "schhtml", "test1.md"),
            os.path.join(tempfile.gettempdir(), "test1.pdf"),
            os.path.join(TEST_PATH, "tests", "schhtml", "wzr", "test1.pdf"),
        ),
        (
            os.path.join(TEST_PATH, "tests", "schhtml", "test2.ihtml"),
            os.path.join(tempfile.gettempdir(), "test2.pdf"),
            os.path.join(TEST_PATH, "tests", "schhtml", "wzr", "test2.pdf"),
        ),
        (
            os.path.join(TEST_PATH, "tests", "schhtml", "test2.ihtml"),
            os.path.join(tempfile.gettempdir(), "test3.docx"),
            os.path.join(TEST_PATH, "tests", "schhtml", "wzr", "test3.docx"),
        ),
        (
            os.path.join(TEST_PATH, "tests", "schhtml", "test4.ihtml"),
            os.path.join(tempfile.gettempdir(), "test4.pdf"),
            os.path.join(TEST_PATH, "tests", "schhtml", "wzr", "test4.pdf"),
        ),
        (
            os.path.join(TEST_PATH, "tests", "schhtml", "test5.md"),
            os.path.join(tempfile.gettempdir(), "test5.pdf"),
            os.path.join(TEST_PATH, "tests", "schhtml", "wzr", "test5.pdf"),
        ),
    )

    def _test(in_file_path, out_file_path, wzr_file_path):
        run(["", "run_schscripts.all2all", in_file_path, "-o", out_file_path])
        if out_file_path.endswith(".pdf"):
            pdf = pdfium.PdfDocument(out_file_path)
            n_pages = len(pdf)
            delta = 0
            for page_number in range(n_pages):
                page = pdf.get_page(page_number)
                pil_image = page.render(
                    scale=1,
                    rotation=0,
                    crop=(0, 0, 0, 0),
                ).to_pil()
                image_path = f"{out_file_path}_{page_number + 1}.png"
                wzr_image_path = f"{wzr_file_path}_{page_number + 1}.png"
                pil_image.save(image_path)

                try:
                    img1 = PIL.Image.open(image_path)
                    img2 = PIL.Image.open(wzr_image_path)

                    delta += compare_images(img1, img2)
                except:
                    delta + 1000
            assert delta < 1
        else:
            soffice_convert(
                out_file_path,
                out_file_path + ".html",
                "html",
            )
            cmp1 = html_content_cmp(out_file_path + ".html", wzr_file_path + ".html")
            assert cmp1

    for in_file_path, out_file_path, wzr_file_path in tests:
        _test(in_file_path, out_file_path, wzr_file_path)


if __name__ == "__main__":
    test_gen_pdf()
    os.chdir(LAST_PATH)
