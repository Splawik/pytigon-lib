from pytigon_lib.schfs.vfstools import *

# Pytest tests
import pytest
import os
import tempfile


def test_norm_path():
    assert norm_path("a/b/../c") == "a/c"
    assert norm_path("a/b/./c") == "a/b/c"
    assert norm_path("a/b/../../c") == "c"
    assert norm_path("") == ""
    assert norm_path(None) == ""


def test_open_file():
    with tempfile.NamedTemporaryFile() as tmp:
        with open_file(tmp.name, "w") as f:
            f.write("test")
        with open_file(tmp.name, "r") as f:
            assert f.read() == "test"


def test_open_and_create_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        file_path = os.path.join(tmpdir, "subdir", "test.txt")
        with open_and_create_dir(file_path, "w") as f:
            f.write("test")
        assert os.path.exists(file_path)


def test_get_unique_filename():
    filename = get_unique_filename("base", "txt")
    assert "base" in filename and "txt" in filename


def test_get_temp_filename():
    filename = get_temp_filename("base", "txt")
    assert "base" in filename and "txt" in filename


def test_delete_from_zip():
    with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
        with zipfile.ZipFile(tmp.name, "w") as zf:
            zf.writestr("test.txt", "content")
        delete_from_zip(tmp.name, ["test.txt"])
        with zipfile.ZipFile(tmp.name, "r") as zf:
            assert "test.txt" not in zf.namelist()


def test_extractall():
    with tempfile.TemporaryDirectory() as tmpdir:
        with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
            with zipfile.ZipFile(tmp.name, "w") as zf:
                zf.writestr("test.txt", "content")
            with zipfile.ZipFile(tmp.name, "r") as zf:
                extractall(zf, tmpdir)
            assert os.path.exists(os.path.join(tmpdir, "test.txt"))


def test_zip_writer():
    with tempfile.NamedTemporaryFile(suffix=".zip") as tmp:
        writer = ZipWriter(tmp.name)
        writer.writestr("test.txt", b"content")
        writer.close()
        with zipfile.ZipFile(tmp.name, "r") as zf:
            assert "test.txt" in zf.namelist()


def test_convert_file():
    with tempfile.NamedTemporaryFile(suffix=".html") as tmp:
        assert (
            convert_file(
                "/app/_schtest/test.md",
                tmp.name,
                input_format="md",
                output_format="html",
                for_vfs_output=False,
            )
            == True
        )
        with open(tmp.name, "r") as f:
            assert "<p>" in f.read()


if __name__ == "__main__":
    pytest.main()
