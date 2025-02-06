from pytigon_lib.schhtml.docxdc import *


# Pytest tests
def test_docx_dc_initialization():
    dc = DocxDc()
    assert dc.document is not None
    assert dc.map is not None


def test_docx_dc_close():
    dc = DocxDc(output_name="test.docx")
    dc.close()
    import os

    assert os.path.exists("test.docx")
    os.remove("test.docx")


def test_docx_dc_annotate():
    dc = DocxDc()
    element = MagicMock()
    element.tag = "p"
    element.parent = MagicMock()
    dc.annotate("end_tag", {"element": element})
    assert dc.document.paragraphs[-1].text == ""


if __name__ == "__main__":
    pytest.main()
