import os
from pytigon.pytigon_run import run
from pytigon_lib.schtools.main_paths import get_main_paths
from pytigon_lib.schtools.images import compare_images

import pypdfium2 as pdfium
import PIL

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


def test_gen_pdf():
    in_file_path = os.path.join(TEST_PATH, "tests", "schhtml", "test1.md")
    out_file_path = os.path.join(TEST_PATH, "tests", "schhtml", "test1.pdf")
    wzr_file_path = os.path.join(TEST_PATH, "tests", "schhtml", "wzr", "test1.pdf")

    run(["", "run_schscripts.all2all", in_file_path, "-o", out_file_path])

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

        img1 = PIL.Image.open(image_path)
        img2 = PIL.Image.open(wzr_image_path)

        delta += compare_images(img1, img2)
    assert delta < 1


if __name__ == "__main__":
    test_gen_pdf()
