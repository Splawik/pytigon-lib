"""Tests for .ptig project-name validation (plan point 1.5).

The project name is taken from the archive's ``*.dist-info`` directory name,
which an attacker controls. It must never be joined into a filesystem path or
used to locate ``manage.py`` unless it matches a conservative alphabet.
"""

import io
import zipfile

import pytest

from pytigon_lib.schtools.install import Ptig


def _ptig_payload(dist_info_name):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        archive.writestr(f"{dist_info_name}/METADATA", "Metadata-Version: 2.1\n")
    # Ptig strips the first line (a packaging header) before opening the zip.
    return b"header\n" + buf.getvalue()


class TestPrjNameValidation:
    def test_valid_name_is_accepted(self):
        ptig = Ptig(io.BytesIO(_ptig_payload("schdevtools-1.0.dist-info")))
        assert ptig.is_ok() is True
        assert ptig.prj_name == "schdevtools"

    def test_unsafe_name_is_rejected(self):
        ptig = Ptig(io.BytesIO(_ptig_payload("bad name-1.0.dist-info")))
        assert ptig.prj_name is None
        assert ptig.is_ok() is False

    def test_traversal_prefix_is_rejected(self):
        ptig = Ptig(io.BytesIO(_ptig_payload("../evil-1.0.dist-info")))
        assert ptig.is_ok() is False

    def test_extract_ptig_refuses_invalid_archive(self):
        ptig = Ptig(io.BytesIO(_ptig_payload("bad name-1.0.dist-info")))
        with pytest.raises(ValueError):
            ptig.extract_ptig()

    def test_extract_ptig_refuses_archive_without_metadata(self):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as archive:
            archive.writestr("other/file.txt", "x")
        ptig = Ptig(io.BytesIO(b"header\n" + buf.getvalue()))
        assert ptig.is_ok() is False
        with pytest.raises(ValueError):
            ptig.extract_ptig()
