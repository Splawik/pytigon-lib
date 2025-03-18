import os
import tempfile
import pathlib

from pytigon.pytigon_run import run
from pytigon_lib.schtest.html_test import html_content_cmp
from pytigon_lib.schtools.main_paths import get_main_paths

TEST_PATH = pathlib.Path(__file__).parent.resolve()

PATHS = get_main_paths()

PRJ_PATH = PATHS["PRJ_PATH"]
PRJ_PATH_ALT = PATHS["PRJ_PATH_ALT"]

if os.path.exists(os.path.join(PRJ_PATH, "schscripts")):
    SCHSCRIPTS_PATH = os.path.join(PRJ_PATH, "schscripts")
else:
    SCHSCRIPTS_PATH = os.path.join(PRJ_PATH_ALT, "schscripts")

LAST_PATH = os.getcwd()
os.chdir(TEST_PATH)


def test_ihtml2html():
    tests = (
        (
            os.path.join(TEST_PATH, "assets", "test.html"),
            os.path.join(tempfile.gettempdir(), "test.ihtml"),
            os.path.join(TEST_PATH, "wzr", "test.ihtml"),
        ),
        (
            os.path.join(TEST_PATH, "wzr", "test.ihtml"),
            os.path.join(tempfile.gettempdir(), "test.html"),
            os.path.join(TEST_PATH, "wzr", "test.html"),
        ),
        (
            os.path.join(TEST_PATH, "assets", "test.py"),
            os.path.join(tempfile.gettempdir(), "test.js"),
            os.path.join(TEST_PATH, "wzr", "test.js"),
        ),
        (
            os.path.join(TEST_PATH, "assets", "test.ijs"),
            os.path.join(tempfile.gettempdir(), "test2.js"),
            os.path.join(TEST_PATH, "wzr", "test2.js"),
        ),
    )

    def _test(in_file_path, out_file_path, wzr_file_path):
        run(["", "run_schscripts.ihtml2html", in_file_path, "-o", out_file_path])
        cmp1 = html_content_cmp(out_file_path, wzr_file_path)
        assert cmp1

    for in_file_path, out_file_path, wzr_file_path in tests:
        _test(in_file_path, out_file_path, wzr_file_path)


if __name__ == "__main__":
    test_ihtml2html()
    os.chdir(LAST_PATH)
